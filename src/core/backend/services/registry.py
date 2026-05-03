"""Registry service for tracking installed models."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


class RegistryError(Exception):
    """Registry operation error."""

    pass


@dataclass
class ModelFile:
    """A single model file."""

    filename: str
    local_path: Path
    file_size: int
    status: Literal["pending", "downloading", "ready", "error"] = "ready"
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ModelRecord:
    """Registered model record."""

    repo_id: str
    files: dict[str, ModelFile] = field(default_factory=dict)
    status: Literal["pending", "downloading", "ready", "error"] = "ready"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None

    @property
    def local_path(self) -> Path:
        """Get first file path for backwards compatibility."""
        if self.files:
            return next(iter(self.files.values())).local_path
        return Path()

    @property
    def file_size(self) -> int:
        """Get total file size for backwards compatibility."""
        return sum(f.file_size for f in self.files.values())


class LocalRegistry:
    """Local registry for tracking installed models."""

    def __init__(self, registry_path: Path | None = None) -> None:
        self.registry_path = registry_path or Path("models/registry.json")
        self._lock = asyncio.Lock()
        self._models: dict[str, ModelRecord] = {}
        self._loaded = False

    async def _ensure_loaded(self) -> None:
        """Ensure registry is loaded."""
        if not self._loaded:
            await self._load()
            self._loaded = True

    async def _load(self) -> None:
        """Load registry from disk."""
        if self.registry_path.exists():
            try:
                with open(self.registry_path) as f:
                    data = json.load(f)
                for repo_id, record in data.get("models", {}).items():
                    files = {}
                    for fn, file_data in record.get("files", {}).items():
                        files[fn] = ModelFile(
                            filename=fn,
                            local_path=Path(file_data["local_path"]),
                            file_size=file_data["file_size"],
                            status=file_data.get("status", "ready"),
                        )
                    self._models[repo_id] = ModelRecord(
                        repo_id=repo_id,
                        files=files,
                        status=record.get("status", "ready"),
                        created_at=datetime.fromisoformat(record["created_at"]),
                        updated_at=datetime.fromisoformat(record["updated_at"]),
                        metadata=record.get("metadata", {}),
                    )
            except (json.JSONDecodeError, KeyError) as e:
                raise RegistryError(f"Corrupted registry: {e}") from e

    async def _save(self) -> None:
        """Save registry to disk."""
        self.registry_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "models": {
                repo_id: {
                    "files": {
                        fn: {
                            "local_path": str(f.local_path),
                            "file_size": f.file_size,
                            "status": f.status,
                        }
                        for fn, f in record.files.items()
                    },
                    "status": record.status,
                    "created_at": record.created_at.isoformat(),
                    "updated_at": record.updated_at.isoformat(),
                    "metadata": record.metadata,
                }
                for repo_id, record in self._models.items()
            }
        }
        with open(self.registry_path, "w") as f:
            json.dump(data, f, indent=2)

    async def register_model(self, model: ModelRecord) -> None:
        """Register a new model."""
        async with self._lock:
            await self._ensure_loaded()
            self._models[model.repo_id] = model
            await self._save()

    async def add_file(
        self, repo_id: str, filename: str, local_path: Path, file_size: int
    ) -> None:
        """Add a file to an existing model."""
        async with self._lock:
            await self._ensure_loaded()
            if repo_id not in self._models:
                self._models[repo_id] = ModelRecord(repo_id=repo_id)
            self._models[repo_id].files[filename] = ModelFile(
                filename=filename,
                local_path=local_path,
                file_size=file_size,
            )
            self._models[repo_id].updated_at = datetime.now()
            await self._save()

    async def delete_file(self, repo_id: str, filename: str) -> bool:
        """Delete a specific file from a model. Returns True if file was deleted."""
        async with self._lock:
            await self._ensure_loaded()
            if repo_id not in self._models:
                return False
            if filename in self._models[repo_id].files:
                del self._models[repo_id].files[filename]
                self._models[repo_id].updated_at = datetime.now()
                await self._save()
                return True
            return False

    async def get_model(self, repo_id: str) -> ModelRecord | None:
        """Get a model by ID."""
        async with self._lock:
            await self._ensure_loaded()
            return self._models.get(repo_id)

    async def update_status(
        self,
        repo_id: str,
        status: Literal["pending", "downloading", "ready", "error"],
        error_message: str | None = None,
    ) -> None:
        """Update model status."""
        async with self._lock:
            await self._ensure_loaded()
            if repo_id in self._models:
                self._models[repo_id].status = status
                self._models[repo_id].updated_at = datetime.now()
                if error_message:
                    self._models[repo_id].error_message = error_message
                await self._save()

    async def list_models(self) -> list[ModelRecord]:
        """List all registered models."""
        async with self._lock:
            await self._ensure_loaded()
            return list(self._models.values())

    async def delete_model(self, repo_id: str, filename: str | None = None) -> bool:
        """Delete a model or specific file from registry."""
        async with self._lock:
            await self._ensure_loaded()
            if repo_id not in self._models:
                return False

            if filename:
                if filename in self._models[repo_id].files:
                    del self._models[repo_id].files[filename]
                    self._models[repo_id].updated_at = datetime.now()
                    await self._save()
                    return True
                return False
            else:
                del self._models[repo_id]
                await self._save()
                return True
