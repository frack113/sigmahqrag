import asyncio
import logging
from pathlib import Path

from llama_index.core.schema import Document

from src.back.worker.base import BaseWorker
from src.back.rag.ingestion import IngestionPipelineBuilder

logger = logging.getLogger(__name__)


class GithubEmbeddingWorker(BaseWorker):
    """Embeds documents from GitHub repositories into Qdrant."""

    async def process(self, task: dict) -> None:
        collection_name = task.get("collection_name", "")
        task_id = task.get("task_id", "")
        org = task.get("org", "")
        repo = task.get("repo", "")

        if not collection_name:
            raise ValueError("collection_name is required for github embeddings")

        parts = collection_name.split("/")
        if len(parts) == 2:
            org = parts[0]
            repo = parts[1]

        base_path = Path("data/github") / org / repo
        if not base_path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {base_path}")

        logger.info(f"[GithubEmbeddingWorker] Embedding {collection_name} from {base_path}")

        registry_entries = self._get_registry_entries(org, repo)
        if not registry_entries:
            logger.info(f"[GithubEmbeddingWorker] No entries in doc_registry for {collection_name}")
            return

        total = len(registry_entries)
        errors = []
        skipped = []

        self.db.upsert_worker_state(
            worker_type="github_embeddings",
            status="running",
            current_task_id=task_id,
            progress_percent=0.0,
        )

        builder = IngestionPipelineBuilder(collection_name=collection_name)

        for idx, entry in enumerate(registry_entries):
            file_name = entry.get("file_name", "")
            file_path = base_path / file_name

            if not file_path.exists():
                logger.warning(f"[GithubEmbeddingWorker] File not found: {file_path}")
                skipped.append(file_name)
                self.db.update_doc_registry_embed_status(entry.get("id"), "error")
                continue

            try:
                doc_text = file_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"[GithubEmbeddingWorker] Error reading {file_path}: {e}")
                errors.append({"file": file_name, "error": str(e)})
                self.db.update_doc_registry_embed_status(entry.get("id"), "error")
                continue

            metadata = {
                "source": "github",
                "collection": collection_name,
                "org": org,
                "repo": repo,
                "content_type": entry.get("content_type", ""),
                "file_name": file_name,
            }

            doc = Document(text=doc_text, metadata=metadata)
            try:
                builder.run(documents=[doc])
                self.db.update_doc_registry_embed_status(entry.get("url_hash"), "embedded")
            except Exception as e:
                logger.error(f"[GithubEmbeddingWorker] Error embedding {file_name}: {e}")
                errors.append({"file": file_name, "error": str(e)})
                self.db.update_doc_registry_embed_status(entry.get("url_hash"), "error")

            processed = idx + 1 - len(errors) - len(skipped)
            progress = (processed / total) * 100 if total > 0 else 0
            self.db.update_worker_progress(
                worker_type="github_embeddings",
                progress_percent=round(progress, 2),
                current_file=file_name,
            )

            await asyncio.sleep(0)

        processed = total - len(errors) - len(skipped)
        self.db.update_worker_progress(
            worker_type="github_embeddings",
            progress_percent=100.0,
        )

        logger.info(
            f"[GithubEmbeddingWorker] Complete: {processed}/{total} embedded, "
            f"{len(errors)} errors, {len(skipped)} skipped"
        )

    def _get_registry_entries(self, org: str, repo: str) -> list[dict]:
        """Get doc_registry entries for a specific GitHub repo pending embedding."""
        return self.db.get_pending_doc_registry(org, repo)
