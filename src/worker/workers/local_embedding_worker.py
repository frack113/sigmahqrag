import logging
from pathlib import Path

from src.shared.config import get_config
from src.worker.workers.embedding_base import EmbeddingWorker
from src.worker.enums import WorkerName

logger = logging.getLogger(__name__)


class LocalEmbeddingWorker(EmbeddingWorker):
    """Embeds documents from a local directory into Qdrant."""

    worker_type = WorkerName.LOCAL_EMBEDDINGS
    collection_name = "local"

    def _get_entries(self, task: dict) -> list[dict]:
        collection_name = task.get("collection_name", self.collection_name)
        return self.db.get_pending_doc_registry(org="local", repo=collection_name)

    def _resolve_file_path(self, entry: dict) -> Path | None:
        cfg = get_config()
        config_base_path = Path(cfg.local_documents_path).resolve()
        task_base_path = self._task.get("base_path")
        base_path = Path(task_base_path) if task_base_path else config_base_path
        file_name = entry.get("file_name", "")
        return base_path / file_name if file_name else None

    def _build_metadata(self, entry: dict, collection_name: str) -> dict:
        return {
            "source": "local",
            "collection": collection_name,
            "file_name": entry.get("file_name", ""),
            "content_type": entry.get("content_type", ""),
        }

    def _update_status(self, entry: dict, status: str) -> None:
        self.db.update_doc_registry_embed_status(entry["url_hash"], status)
