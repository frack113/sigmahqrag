"""Embedding manager service."""

from __future__ import annotations

import shutil
from pathlib import Path

from src.back.database import DatabaseService
from src.back.models.download import HFDownloadService
from src.back.models.exceptions import DownloadError
from src.back.models.types import HFRepo
from src.shared import EMBEDDINGS_DIR


class EmbeddingManager:
    """Manager for embedding models."""

    def __init__(self, embeddings_dir: Path | None = None) -> None:
        self.embeddings_dir = embeddings_dir or EMBEDDINGS_DIR
        self.embeddings_dir.mkdir(parents=True, exist_ok=True)
        self.download_service = HFDownloadService()

    async def _load_registry(self) -> dict:
        db = DatabaseService.get_instance()
        if db is None:
            return {}
        models = db.get_models()
        registry = {}
        for m in models:
            if m["model_type"] == "embeddings":
                repo_id = m["repo_id"]
                entry = {
                    "local_path": m.get("local_path"),
                    "file_size": m.get("file_size", 0),
                    "status": m.get("status", "ready"),
                }
                dim = m.get("dimension")
                if dim is not None:
                    entry["dimension"] = dim
                index_path = m.get("index_path")
                if index_path:
                    entry["index_path"] = index_path
                registry[repo_id] = entry
        return registry

    async def _save_registry(self, data: dict) -> None:
        db = DatabaseService.get_instance()
        if db is None:
            return
        for repo_id, record in data.items():
            entry = {
                "repo_id": repo_id,
                "model_type": "embeddings",
                "local_path": record.get("local_path"),
                "file_size": record.get("file_size", 0),
                "status": record.get("status", "ready"),
                "dimension": record.get("dimension"),
                "index_path": record.get("index_path"),
            }
            db.upsert_model(entry)

    async def search_models(
        self, query: str = "sentence-transformers", limit: int = 10
    ) -> list[HFRepo]:
        """Search for embedding models."""
        return await self.download_service.list_models(query)

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
    ) -> dict:
        """Download an embedding model.

        Raises:
            DownloadError: If repo_id format is invalid
        """
        try:
            repo = HFRepo.from_string(repo_id)
        except ValueError as e:
            raise DownloadError(f"Invalid repo_id '{repo_id}': {e}") from e
        temp_dir = self.embeddings_dir / "temp" / repo.owner / repo.name
        temp_dir.mkdir(parents=True, exist_ok=True)
        downloaded_path = self.download_service.download_repo(repo, temp_dir)
        temp_path = Path(downloaded_path)

        final_dir = self.embeddings_dir / repo.owner / repo.name
        final_dir.mkdir(parents=True, exist_ok=True)

        if temp_path.exists() and not temp_path.is_dir():
            dest = final_dir / temp_path.name
            shutil.move(str(temp_path), str(dest))
        else:
            if final_dir.exists():
                shutil.rmtree(final_dir)
            shutil.move(str(temp_path), str(final_dir))
            dest = final_dir

        dimension = 384
        index_path = None

        if create_index:
            index_path = await self._create_index(dest, dimension)

        temp_parent = self.embeddings_dir / "temp"
        if temp_parent.exists():
            shutil.rmtree(temp_parent)

        record = {
            "repo_id": repo_id,
            "local_path": str(dest),
            "file_size": dest.stat().st_size,
            "status": "ready",
            "dimension": dimension,
            "index_path": str(index_path) if index_path else None,
        }

        registry = await self._load_registry()
        total_size = sum(f.stat().st_size for f in dest.rglob("*") if f.is_file())
        registry[repo_id] = {
            "local_path": str(dest),
            "file_size": total_size,
            "status": "ready",
            "dimension": dimension,
            "index_path": str(index_path) if index_path else None,
        }
        await self._save_registry(registry)

        return record

    async def list_installed(self) -> dict:
        """List installed embedding models."""
        await self._sync_with_folder()
        return await self._load_registry()

    async def _sync_with_folder(self) -> None:
        """Scan embeddings folder and add any unregistered models."""
        registry = await self._load_registry()
        if not self.embeddings_dir.exists():
            return

        for model_dir in self.embeddings_dir.iterdir():
            if not model_dir.is_dir():
                continue
            if model_dir.name.startswith("."):
                continue
            if model_dir.name in ("cache", "temp", "embeddings_registry.json"):
                continue

            for sub_dir in model_dir.iterdir():
                if not sub_dir.is_dir():
                    continue
                if sub_dir.name.startswith("."):
                    continue
                if sub_dir.name in ("cache", "temp", "embeddings_registry.json"):
                    continue

                repo_id = f"{model_dir.name}/{sub_dir.name}"
                if repo_id not in registry:
                    files = list(sub_dir.rglob("*"))
                    file_count = sum(1 for f in files if f.is_file())
                    if file_count > 0:
                        total_size = sum(f.stat().st_size for f in files if f.is_file())
                        registry[repo_id] = {
                            "local_path": str(sub_dir),
                            "status": "ready",
                            "file_size": total_size,
                        }

        await self._save_registry(registry)

    async def get_repo_files(self, repo_id: str) -> list[str]:
        """Get list of files in an embedding model repo."""
        try:
            repo = HFRepo.from_string(repo_id)
        except ValueError as e:
            raise DownloadError(f"Invalid repo_id '{repo_id}': {e}") from e
        api = self.download_service.get_model_info(repo)
        if api.siblings:
            return [f.rfilename for f in api.siblings]
        return []

    async def delete_model(self, repo_id: str) -> None:
        """Delete an embedding model."""
        registry = await self._load_registry()
        if repo_id in registry:
            path = Path(registry[repo_id]["local_path"])
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()
            index_path = registry[repo_id].get("index_path")
            if index_path and Path(index_path).exists():
                Path(index_path).unlink()
            del registry[repo_id]
            await self._save_registry(registry)
