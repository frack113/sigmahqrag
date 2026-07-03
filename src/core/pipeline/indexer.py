"""Unified document indexer — reads from DuckDB, transforms, embeds, stores in Qdrant.

Routing is driven by IndexRoute dataclass and TransformRegistry.
Storage uses a single store_embeddings() call for all collection types.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from src.config.settings import get_config
from src.core import TransformRegistry
from src.core.base import TransformConfig
from src.core.document.parser.generic_parser import GenericTransform
from src.core.pipeline.ingestion import IngestionPipelineBuilder
from src.infrastructure.database import DatabaseService
from src.shared.utils.identify_file_type import FILETYPE_TO_SUBDIR

logger = logging.getLogger(__name__)


@dataclass
class IndexRoute:
    """Declarative route: which DuckDB table feeds which Qdrant collection.

    Attributes:
        table_name: DuckDB table to read pending entries from.
        qdrant_collection: Target Qdrant collection name.
        content_type: Optional filter on content_type column.
    """

    table_name: str
    qdrant_collection: str
    content_type: str | None = None


ROUTES: list[IndexRoute] = [
    IndexRoute("doc_registry", "sigma_rules", content_type="sigma_rule"),
    IndexRoute("doc_registry", "sigma_docs"),
    IndexRoute("sigma_spec", "sigma_spec"),
]


@dataclass
class IndexResult:
    """Result for a single index route."""

    route: IndexRoute
    processed: int = 0
    errors: list[str] = field(default_factory=list)


class UnifiedIndexer:
    """Indexes pending documents from DuckDB into Qdrant.

    The indexer is parameter-free: it reads ROUTES which map
    (table, content_type_filter) → (Qdrant collection).
    Transform selection is delegated to TransformRegistry.find_for_file().
    """

    def __init__(
        self,
        db: DatabaseService | None = None,
    ) -> None:
        self.db = db or DatabaseService.get_instance()

    async def index(self, route: IndexRoute) -> IndexResult:
        """Execute a single index route."""
        result = IndexResult(route=route)

        rows = self._get_pending(route)
        if not rows:
            logger.info("No pending entries for %s → %s", route.table_name, route.qdrant_collection)
            return result

        for row in rows:
            try:
                file_path = self._resolve_path(route.table_name, row)
                if file_path is None or not file_path.exists():
                    logger.warning(
                        "File not found for %s: %s", row.get("url_hash"), row.get("file_name")
                    )
                    continue

                transform_cls = TransformRegistry.find_for_file(file_path)
                if transform_cls is None:
                    transform_cls = GenericTransform

                base_config = transform_cls._build_default_config()
                route_config = TransformConfig(
                    collection_name=route.qdrant_collection,
                    collection=route.qdrant_collection,
                    model_name=base_config.model_name,
                    chunk_size=base_config.chunk_size,
                    chunk_overlap=base_config.chunk_overlap,
                    batch_size=base_config.batch_size,
                    max_length=base_config.max_length,
                    enable_sbert=base_config.enable_sbert,
                    enable_eval_questions=base_config.enable_eval_questions,
                    llm_client=base_config.llm_client,
                    max_heading_level=base_config.max_heading_level,
                )
                transform = transform_cls(config=route_config)
                docs = transform.run(file_path)
                if not docs:
                    continue

                # Some transforms (notably SigmaParser → SigmaChunker) may emit
                # chunks with empty text (missing fields). The pipeline filters
                # those out internally, but we skip empties early to avoid the
                # embedding step cost.
                non_empty = [d for d in docs if d.text]
                if not non_empty:
                    continue

                builder = IngestionPipelineBuilder(
                    collection_name=route.qdrant_collection,
                )
                nodes = builder.run(non_empty)

                if not nodes:
                    logger.warning(
                        "Pipeline produced no nodes for %s (%s)",
                        row.get("file_name"),
                        route.qdrant_collection,
                    )
                    continue

                self._update_status(route.table_name, row, "embedded")
                result.processed += 1

            except Exception as e:
                logger.error("Failed to index %s: %s", row.get("url_hash"), e)
                result.errors.append(str(e))
                self._update_status(route.table_name, row, "error")

        return result

    async def index_all(self, group: str | None = None) -> list[IndexResult]:
        """Execute configured routes, optionally filtered by group ("spec" or "docs")."""
        if group == "spec":
            routes = [r for r in ROUTES if r.table_name == "sigma_spec"]
        elif group == "docs":
            routes = [r for r in ROUTES if r.table_name == "doc_registry"]
        else:
            routes = ROUTES
        results: list[IndexResult] = []
        for route in routes:
            r = await self.index(route)
            results.append(r)
        return results

    def _get_pending(self, route: IndexRoute) -> list[dict]:
        """Fetch pending entries for a given route."""
        if route.table_name == "sigma_spec":
            return self.db.get_pending_sigma_spec()
        return self.db.get_pending_by_content_type(route.content_type)

    def _resolve_path(self, table_name: str, row: dict) -> Path | None:
        """Resolve the on-disk file path for a given entry."""
        cfg = get_config()
        file_name: str = row.get("file_name", "") or ""

        if table_name == "sigma_spec":
            org: str = row.get("org", "") or ""
            repo: str = row.get("repo", "") or ""
            if org and repo:
                return Path(cfg.paths_spec_repos_dir).resolve() / org / repo / file_name
            return Path(cfg.paths_sigma_spec_dir).resolve() / file_name

        org = row.get("org", "") or ""

        if org == "local":
            return Path(cfg.local_documents_path).resolve() / file_name

        if org == "sigmaref":
            base = Path(cfg.sigmaref_documents_path).resolve()
            subdir = FILETYPE_TO_SUBDIR.get(row.get("content_type", ""), "misc")
            candidate = base / subdir / file_name
            if candidate.exists():
                return candidate
            return base / file_name

        repo = row.get("repo", "") or ""
        if org and repo:
            return Path(cfg.paths_github_dir) / org / repo / file_name

        return None

    def _update_status(self, table_name: str, row: dict, status: str) -> None:
        """Update embed_status for a given entry."""
        url_hash: str = row.get("url_hash") or row.get("hash", "")
        if not url_hash:
            return
        if table_name == "sigma_spec":
            self.db.update_spec_status(url_hash, status)
        else:
            self.db.update_doc_registry_embed_status(url_hash, status)
