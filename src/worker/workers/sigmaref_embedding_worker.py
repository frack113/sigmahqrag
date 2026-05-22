import logging
from pathlib import Path

from src.worker.workers.embedding_base import EmbeddingWorker
from src.worker.enums import WorkerName

logger = logging.getLogger(__name__)


class SigmaRefEmbeddingWorker(EmbeddingWorker):
    """Embeds Sigma Reference documents from doc_sigma_ref into Qdrant."""

    worker_type = WorkerName.SIGMAREF_EMBEDDINGS
    collection_name = "sigma_doc"

    def _get_entries(self, task: dict) -> list[dict]:
        raw_entries = self.db.get_pending_sigma_ref()
        if not raw_entries:
            return []

        result = []
        for e in raw_entries:
            url_hash = e.get("url_hash") or ""
            if not url_hash:
                continue
            result.append(
                {
                    "hash": url_hash,
                    "file_name": f"{url_hash}.md",
                    **{k: v for k, v in e.items() if k not in ("url_hash",)},
                }
            )
        return result

    def _resolve_file_path(self, entry: dict) -> Path | None:
        registry_path = Path(self._task.get("registry_path", "data/documents/sigmaref"))
        file_hash = entry.get("hash") or ""
        file_name = entry.get("file_name") or ""

        if not file_hash and not file_name:
            return None

        for candidate in (registry_path / file_name, registry_path / file_hash):
            if candidate == registry_path:
                continue
            if candidate.exists():
                return candidate

        matches = sorted(registry_path.glob(f"{file_hash}.*"))
        return matches[0] if matches else registry_path / f"{file_hash}.md"

    def _build_metadata(self, entry: dict, collection_name: str) -> dict:
        metadata = dict(entry)
        metadata.pop("hash", None)
        metadata["source"] = "sigmaref"
        metadata["collection"] = collection_name
        return metadata

    def _update_status(self, entry: dict, status: str) -> None:
        self.db.update_sigma_ref_embed_status(entry.get("hash", ""), status)
