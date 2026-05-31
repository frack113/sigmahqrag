"""Unified embedding worker for all document sources."""

from __future__ import annotations

import logging
from pathlib import Path
from src.shared.config import get_config
from src.worker.workers.embedding_base import EmbeddingWorker
from src.worker.enums import WorkerName

logger = logging.getLogger(__name__)


class GenericEmbeddingWorker(EmbeddingWorker):
    """
    Unified embedding worker supporting multiple document sources.

    Usage::

        # All pending docs
        GenericEmbeddingWorker()
        # or
        worker = GenericEmbeddingWorker()
        worker.process({})

        # Only local docs
        GenericEmbeddingWorker()
        worker.process({"org": "local", "collection_name": "local"})

        # Only specific repo
        GenericEmbeddingWorker()
        worker.process({"org": "google", "repo": "sigmac"})
    """

    worker_type: WorkerName = WorkerName.LOCAL_EMBEDDINGS
    collection_name: str = ""

    def _get_entries(self, task: dict) -> list[dict]:
        org = task.get("org")
        repo = task.get("repo")
        collection_name = task.get("collection_name", self.collection_name)

        if org == "local":
            return self.db.get_pending_doc_registry(org="local", repo=collection_name)

        if org == "sigmaref":
            raw_entries = self.db.get_pending_entries(org="sigmaref")
            if not raw_entries:
                return []
            result = []
            for e in raw_entries:
                url_hash = e.get("url_hash") or ""
                file_name = e.get("file_name") or f"{url_hash}.md"
                if not url_hash:
                    continue
                result.append(
                    {
                        "hash": url_hash,
                        "file_name": file_name,
                        **{k: v for k, v in e.items() if k not in ("url_hash", "file_name")},
                    }
                )
            return result

        if org and repo:
            base_path = Path(get_config().paths_github_dir) / org / repo
            if not base_path.exists():
                raise FileNotFoundError(f"Repository path does not exist: {base_path}")
            return self.db.get_pending_doc_registry(org, repo)

        if org and collection_name == "all":
            all_pending = self.db.get_pending_registry_all()
            return [
                e for e in all_pending if e.get("org") and e.get("org") not in ("local", "sigmaref")
            ]

        # Fallback: all pending
        return self.db.get_pending_registry_all()

    def _resolve_file_path(self, entry: dict) -> Path | None:
        cfg = get_config()
        org = entry.get("org", "")
        file_name = entry.get("file_name", "")

        if not file_name:
            url_hash = entry.get("url_hash", "") or entry.get("hash", "")
            file_name = url_hash

        source_type = entry.get("source", "")

        if source_type == "local" or org == "local":
            config_base_path = Path(cfg.local_documents_path).resolve()
            task_base_path = self._task.get("base_path")
            base_path = Path(task_base_path) if task_base_path else config_base_path
            return base_path / file_name

        if org == "sigmaref":
            registry_path = Path(cfg.sigmaref_documents_path).resolve()
            task_registry = self._task.get("registry_path")
            if task_registry:
                registry_path = Path(task_registry)

            file_hash = entry.get("hash", "")
            if file_hash:
                for candidate in (registry_path / file_hash, registry_path / f"{file_hash}.md"):
                    if candidate.exists():
                        return candidate
                matches = sorted(registry_path.glob(f"{file_hash}.*"))
                if matches:
                    return matches[0]

            if file_name:
                candidate = registry_path / file_name
                if candidate.exists():
                    return candidate

            return registry_path / f"{file_hash}.md" if file_hash else None

        # GitHub
        if org:
            repo = entry.get("repo", "")
            if repo:
                return Path(cfg.paths_github_dir) / org / repo / file_name

        return None

    def _build_metadata(self, entry: dict, collection_name: str) -> dict:
        org = entry.get("org", "")

        if org == "local":
            return {
                "source": "local",
                "collection": collection_name,
                "file_name": entry.get("file_name", ""),
                "content_type": entry.get("content_type", ""),
            }

        if org == "sigmaref":
            metadata = dict(entry)
            metadata.pop("hash", None)
            metadata["source"] = "sigma_docs"
            metadata["collection"] = collection_name
            return metadata

        # GitHub
        parts = collection_name.split("/")
        gh_org, gh_repo = (parts[0], parts[1]) if len(parts) == 2 else (org, entry.get("repo", ""))
        return {
            "source": "github",
            "collection": collection_name,
            "org": gh_org,
            "repo": gh_repo,
            "content_type": entry.get("content_type", ""),
            "file_name": entry.get("file_name", ""),
        }

    def _update_status(self, entry: dict, status: str) -> None:
        doc_id = entry.get("url_hash") or entry.get("hash", "")
        if doc_id:
            self.db.update_doc_registry_embed_status(doc_id, status)
