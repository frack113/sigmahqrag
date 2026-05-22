"""Unified model registry for LLM and embeddings."""

from __future__ import annotations

from pathlib import Path

from src.back.database import DatabaseService


class UnifiedRegistry:
    """Unified registry for LLM and embedding models."""

    _instance: UnifiedRegistry | None = None

    @classmethod
    def get_instance(cls) -> UnifiedRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance for testing purposes."""
        cls._instance = None

    def __init__(self) -> None:
        self._registry: dict[str, dict[str, dict]] = {"llm": {}, "embeddings": {}}
        self._loaded = False

    def _ensure_loaded(self, db: DatabaseService) -> None:
        if self._loaded:
            return
        self._loaded = True
        models = db.get_models()
        for m in models:
            repo_id = m["repo_id"]
            model_type = m["model_type"]
            entry = {
                "local_path": m.get("local_path"),
                "file_size": m.get("file_size", 0),
                "status": m.get("status", "ready"),
            }
            if model_type == "llm":
                files = m.get("files")
                if files:
                    entry["files"] = files
            elif model_type == "embeddings":
                dim = m.get("dimension")
                if dim is not None:
                    entry["dimension"] = dim
                index_path = m.get("index_path")
                if index_path:
                    entry["index_path"] = index_path
            if model_type == "llm":
                self._registry["llm"][repo_id] = entry
            elif model_type == "embeddings":
                self._registry["embeddings"][repo_id] = entry

    def reload(self, db: DatabaseService) -> None:
        """Force a reload of the registry from the database."""
        self._loaded = False
        self._ensure_loaded(db)

    def _load(self, db: DatabaseService) -> None:
        self._ensure_loaded(db)

    def _save(self, db: DatabaseService) -> None:
        for model_type in ("llm", "embeddings"):
            for repo_id, record in self._registry[model_type].items():
                data = {
                    "repo_id": repo_id,
                    "model_type": model_type,
                    "local_path": record.get("local_path"),
                    "file_size": record.get("file_size", 0),
                    "status": record.get("status", "ready"),
                }
                if model_type == "embeddings":
                    data["dimension"] = record.get("dimension")
                    data["index_path"] = record.get("index_path")
                db.upsert_model(data)

    def get_llm(self, repo_id: str, db: DatabaseService) -> dict | None:
        self._ensure_loaded(db)
        return self._registry["llm"].get(repo_id)

    def get_embedding(self, repo_id: str, db: DatabaseService) -> dict | None:
        self._ensure_loaded(db)
        return self._registry["embeddings"].get(repo_id)

    def list_llms(self, db: DatabaseService) -> dict[str, dict]:
        self._ensure_loaded(db)
        return self._registry["llm"]

    def list_embeddings(self, db: DatabaseService) -> dict[str, dict]:
        self._ensure_loaded(db)
        return self._registry["embeddings"]

    def add_llm(self, repo_id: str, record: dict, db: DatabaseService) -> None:
        self._ensure_loaded(db)
        self._registry["llm"][repo_id] = record
        self._save(db)

    def add_embedding(self, repo_id: str, record: dict, db: DatabaseService) -> None:
        self._ensure_loaded(db)
        self._registry["embeddings"][repo_id] = record
        self._save(db)

    def remove_llm(self, repo_id: str, db: DatabaseService) -> bool:
        self._ensure_loaded(db)
        if repo_id in self._registry["llm"]:
            del self._registry["llm"][repo_id]
            db.delete_model(repo_id)
            return True
        return False

    def remove_embedding(self, repo_id: str, db: DatabaseService) -> bool:
        self._ensure_loaded(db)
        if repo_id in self._registry["embeddings"]:
            del self._registry["embeddings"][repo_id]
            db.delete_model(repo_id)
            return True
        return False

    def sync_llm_folder(self, llm_dir: Path, db: DatabaseService, save: bool = True) -> None:
        self._ensure_loaded(db)
        if not llm_dir.exists():
            return

        for model_dir in llm_dir.iterdir():
            if not model_dir.is_dir() or model_dir.name.startswith("."):
                continue
            if model_dir.name in ("cache", "temp"):
                continue

            for sub_dir in model_dir.iterdir():
                if not sub_dir.is_dir() or sub_dir.name.startswith("."):
                    continue
                if sub_dir.name in ("cache", "temp"):
                    continue

                repo_id = f"{model_dir.name}/{sub_dir.name}"
                files = {}
                total_size = 0

                for f in sub_dir.rglob("*"):
                    if not f.is_file():
                        continue
                    if f.suffix != ".gguf":
                        continue
                    if f.name.startswith("."):
                        continue
                    size = f.stat().st_size
                    total_size += size
                    files[f.name] = {
                        "filename": f.name,
                        "local_path": str(f),
                        "file_size": size,
                        "status": "ready",
                    }

                if files:
                    if repo_id not in self._registry["llm"]:
                        self._registry["llm"][repo_id] = {
                            "local_path": str(sub_dir),
                            "files": files,
                        }

        if save:
            self._save(db)

    def sync_embeddings_folder(
        self, embeddings_dir: Path, db: DatabaseService, save: bool = True
    ) -> None:
        self._ensure_loaded(db)
        if not embeddings_dir.exists():
            return

        for model_dir in embeddings_dir.iterdir():
            if not model_dir.is_dir() or model_dir.name.startswith("."):
                continue
            if model_dir.name in ("cache", "temp"):
                continue

            for sub_dir in model_dir.iterdir():
                if not sub_dir.is_dir() or sub_dir.name.startswith("."):
                    continue
                if sub_dir.name in ("cache", "temp"):
                    continue

                repo_id = f"{model_dir.name}/{sub_dir.name}"
                if repo_id not in self._registry["embeddings"]:
                    files = list(sub_dir.rglob("*"))
                    file_count = sum(1 for f in files if f.is_file())
                    if file_count > 0:
                        self._registry["embeddings"][repo_id] = {
                            "local_path": str(sub_dir),
                        }

        if save:
            self._save(db)
