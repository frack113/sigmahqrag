import logging
from pathlib import Path

from src.worker.workers.embedding_base import EmbeddingWorker

logger = logging.getLogger(__name__)


class LocalEmbeddingWorker(EmbeddingWorker):
    """Embeds documents from a local directory into Qdrant."""

    worker_type = "local_embeddings"
    collection_name = "local"

    def _get_entries(self, task: dict) -> list[dict]:
        collection_name = task.get("collection_name", self.collection_name)
        all_entries = self.db.get_doc_sigma_ref(limit=10000)
        return [
            e
            for e in all_entries
            if e.get("org") == "local"
            and e.get("repo") == collection_name
            and e.get("embed_status") == "discovered"
        ]

    def _resolve_file_path(self, entry: dict) -> Path | None:
        base_path = Path(self._task.get("base_path", "data/documents/local"))
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
        pass  # Local embedding status not tracked in DB
