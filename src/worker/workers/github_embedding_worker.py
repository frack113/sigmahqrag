import logging
from pathlib import Path

from src.worker.workers.embedding_base import EmbeddingWorker
from src.worker.enums import WorkerName

logger = logging.getLogger(__name__)


class GithubEmbeddingWorker(EmbeddingWorker):
    """Embeds documents from GitHub repositories into Qdrant."""

    worker_type = WorkerName.GITHUB_EMBEDDINGS

    def _get_entries(self, task: dict) -> list[dict]:
        collection_name = task.get("collection_name", "")
        if not collection_name:
            raise ValueError("collection_name is required for github embeddings")

        if collection_name == "all":
            all_pending = self.db.get_pending_sigma_ref()
            return [
                e for e in all_pending
                if e.get("org") and e.get("org") not in ("local", "sigmaref")
            ]

        parts = collection_name.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid collection_name format: {collection_name}")
        org, repo = parts[0], parts[1]

        base_path = Path("data/github") / org / repo
        if not base_path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {base_path}")

        return self.db.get_pending_sigma_ref(org, repo)

    def _resolve_file_path(self, entry: dict) -> Path | None:
        org = entry.get("org") or ""
        repo = entry.get("repo") or ""
        file_name = entry.get("file_name") or ""
        if not org or not repo or not file_name:
            return None
        return Path("data/github") / org / repo / file_name

    def _build_metadata(self, entry: dict, collection_name: str) -> dict:
        parts = collection_name.split("/")
        org, repo = (parts[0], parts[1]) if len(parts) == 2 else ("", "")
        return {
            "source": "github",
            "collection": collection_name,
            "org": org,
            "repo": repo,
            "content_type": entry.get("content_type", ""),
            "file_name": entry.get("file_name", ""),
        }

    def _update_status(self, entry: dict, status: str) -> None:
        self.db.update_sigma_ref_embed_status(entry.get("url_hash", ""), status)
