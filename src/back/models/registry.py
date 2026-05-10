"""Unified model registry for LLM and embeddings."""

from __future__ import annotations

import json
from pathlib import Path


class UnifiedRegistry:
    """Unified registry for LLM and embedding models."""

    def __init__(self, registry_path: Path | None = None) -> None:
        self._registry_path = registry_path or Path("data/models/registry.json")
        self._registry: dict[str, dict[str, dict]] = {"llm": {}, "embeddings": {}}
        self._load()

    def _load(self) -> None:
        if self._registry_path.exists():
            with open(self._registry_path) as f:
                self._registry = json.load(f)
        if "llm" not in self._registry:
            self._registry["llm"] = {}
        if "embeddings" not in self._registry:
            self._registry["embeddings"] = {}

    def _save(self) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._registry_path, "w") as f:
            json.dump(self._registry, f, indent=2)

    def get_llm(self, repo_id: str) -> dict | None:
        return self._registry["llm"].get(repo_id)

    def get_embedding(self, repo_id: str) -> dict | None:
        return self._registry["embeddings"].get(repo_id)

    def list_llms(self) -> dict[str, dict]:
        return self._registry["llm"]

    def list_embeddings(self) -> dict[str, dict]:
        return self._registry["embeddings"]

    def add_llm(self, repo_id: str, record: dict) -> None:
        self._registry["llm"][repo_id] = record
        self._save()

    def add_embedding(self, repo_id: str, record: dict) -> None:
        self._registry["embeddings"][repo_id] = record
        self._save()

    def remove_llm(self, repo_id: str) -> bool:
        if repo_id in self._registry["llm"]:
            del self._registry["llm"][repo_id]
            self._save()
            return True
        return False

    def remove_embedding(self, repo_id: str) -> bool:
        if repo_id in self._registry["embeddings"]:
            del self._registry["embeddings"][repo_id]
            self._save()
            return True
        return False

    def sync_llm_folder(self, llm_dir: Path) -> None:
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

        self._save()

    def sync_embeddings_folder(self, embeddings_dir: Path) -> None:
        if not embeddings_dir.exists():
            return

        for model_dir in embeddings_dir.iterdir():
            if not model_dir.is_dir() or model_dir.name.startswith("."):
                continue
            if model_dir.name in ("cache", "temp", "embeddings_registry.json"):
                continue

            for sub_dir in model_dir.iterdir():
                if not sub_dir.is_dir() or sub_dir.name.startswith("."):
                    continue
                if sub_dir.name in ("cache", "temp", "embeddings_registry.json"):
                    continue

                repo_id = f"{model_dir.name}/{sub_dir.name}"
                if repo_id not in self._registry["embeddings"]:
                    files = list(sub_dir.rglob("*"))
                    file_count = sum(1 for f in files if f.is_file())
                    if file_count > 0:
                        self._registry["embeddings"][repo_id] = {
                            "local_path": str(sub_dir),
                        }

        self._save()


def create_unified_registry() -> UnifiedRegistry:
    return UnifiedRegistry()
