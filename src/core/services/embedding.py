"""Embedding manager service."""

from __future__ import annotations

from pathlib import Path

from src.config import EMBEDDINGS_DIR

from .download import HFDownloadService
from .registry import ModelRecord


class EmbeddingManager:
    """Manager for embedding models."""

    def __init__(self, embeddings_dir: Path | None = None) -> None:
        self.embeddings_dir = embeddings_dir or EMBEDDINGS_DIR
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = Path("models/embeddings_registry.json")
        self.download_service = HFDownloadService()

    async def _load_registry(self) -> dict:
        """Load embeddings registry."""
        if self._registry_path.exists():
            import json

            with open(self._registry_path) as f:
                return json.load(f)
        return {}

    async def _save_registry(self, data: dict) -> None:
        """Save embeddings registry."""
        import json

        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._registry_path, "w") as f:
            json.dump(data, f, indent=2)

    async def search_models(
        self, query: str = "sentence-transformers", limit: int = 10
    ):
        """Search for embedding models."""
        return await self.download_service.list_models(query, limit=limit)

    async def _create_index(self, model_path: Path, dimension: int = 384) -> Path:
        """Create FAISS index for embeddings."""
        try:
            import faiss

            index = faiss.IndexFlatL2(dimension)
            index_path = model_path.parent / "index.faiss"
            faiss.write_index(index, str(index_path))
            return index_path
        except ImportError:
            return model_path.parent / "index.npy"

    async def download_model(
        self,
        repo_id: str,
        filename: str | None = None,
        create_index: bool = True,
    ) -> ModelRecord:
        """Download an embedding model."""
        temp_path = Path(self.download_service.download(repo_id, filename))

        final_dir = self.embeddings_dir / repo_id.replace("/", "_")
        final_dir.mkdir(parents=True, exist_ok=True)
        dest = final_dir / temp_path.name
        temp_path.rename(dest)

        dimension = 384
        index_path = None

        if create_index:
            index_path = await self._create_index(dest, dimension)

        record = ModelRecord(
            repo_id=repo_id,
            local_path=dest,
            file_size=dest.stat().st_size,
            status="ready",
        )

        registry = await self._load_registry()
        registry[repo_id] = {
            "local_path": str(dest),
            "file_size": dest.stat().st_size,
            "status": "ready",
            "dimension": dimension,
            "index_path": str(index_path) if index_path else None,
        }
        await self._save_registry(registry)

        return record

    async def list_installed(self) -> dict:
        """List installed embedding models."""
        return await self._load_registry()

    async def delete_model(self, repo_id: str) -> None:
        """Delete an embedding model."""
        registry = await self._load_registry()
        if repo_id in registry:
            path = Path(registry[repo_id]["local_path"])
            if path.exists():
                path.unlink()
            index_path = registry[repo_id].get("index_path")
            if index_path and Path(index_path).exists():
                Path(index_path).unlink()
            del registry[repo_id]
            await self._save_registry(registry)
