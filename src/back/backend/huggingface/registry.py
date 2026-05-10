"""Registry service for tracking installed models."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal


class RegistryError(Exception):
    """Registry operation error."""

    pass


class ModelNotFoundError(Exception):
    """Model not found in registry."""

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


class LocalRegistry:
    """Local file-based model registry."""

    def __init__(self, registry_path: Path | None = None) -> None:
        """Initialize local registry."""
        self._registry_path = registry_path or Path("models/registry.json")
        self._registry: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """Load registry from disk."""
        if self._registry_path.exists():
            with open(self._registry_path) as f:
                self._registry = json.load(f)

    def _save(self) -> None:
        """Save registry to disk."""
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._registry_path, "w") as f:
            json.dump(self._registry, f, indent=2)

    def get(self, repo_id: str) -> dict | None:
        """Get model record by repo_id."""
        return self._registry.get(repo_id)

    def list_all(self) -> list[dict]:
        """List all registered models."""
        return list(self._registry.values())

    def add(self, repo_id: str, record: dict) -> None:
        """Add or update a model record."""
        self._registry[repo_id] = record
        self._save()

    def remove(self, repo_id: str) -> bool:
        """Remove a model record."""
        if repo_id in self._registry:
            del self._registry[repo_id]
            self._save()
            return True
        return False

    def update_status(self, repo_id: str, status: str) -> None:
        """Update model status."""
        if repo_id in self._registry:
            self._registry[repo_id]["status"] = status
            self._save()


class ModelRegistry:
    """Registry for managing installed models."""

    def __init__(self, registry_path: Path | None = None) -> None:
        """Initialize the model registry."""
        self._registry_path = registry_path or Path("models/registry.json")
        self._registry: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        """Load registry from disk."""
        if self._registry_path.exists():
            with open(self._registry_path) as f:
                self._registry = json.load(f)

    def _save(self) -> None:
        """Save registry to disk."""
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._registry_path, "w") as f:
            json.dump(self._registry, f, indent=2)

    def get(self, repo_id: str) -> dict | None:
        """Get model record by repo_id."""
        return self._registry.get(repo_id)

    def list_all(self) -> list[dict]:
        """List all registered models."""
        return list(self._registry.values())

    def add(self, repo_id: str, record: dict) -> None:
        """Add or update a model record."""
        self._registry[repo_id] = record
        self._save()

    def remove(self, repo_id: str) -> bool:
        """Remove a model record."""
        if repo_id in self._registry:
            del self._registry[repo_id]
            self._save()
            return True
        return False

    def update_status(self, repo_id: str, status: str) -> None:
        """Update model status."""
        if repo_id in self._registry:
            self._registry[repo_id]["status"] = status
            self._save()


class ModelManager:
    """Manager for LLM models from HuggingFace."""

    def __init__(
        self,
        registry: LocalRegistry | None = None,
        download_service: Any = None,
    ) -> None:
        """Initialize model manager."""
        self.registry = registry or LocalRegistry()
        self.download_service = download_service

    async def list_installed_models(self) -> list[ModelRecord]:
        """List all installed models."""
        records = []
        for repo_id, data in self.registry._registry.items():
            files = {
                name: ModelFile(
                    filename=name,
                    local_path=Path(info["local_path"]),
                    file_size=info.get("file_size", 0),
                    status=info.get("status", "ready"),
                )
                for name, info in data.get("files", {}).items()
            }
            records.append(
                ModelRecord(
                    repo_id=repo_id,
                    files=files,
                    status=data.get("status", "ready"),
                )
            )
        return records

    async def download_model(
        self,
        repo_id: str,
        filename: str | None = None,
        expected_hash: str | None = None,
    ) -> None:
        """Download a model."""
        pass

    async def get_model_info(self, repo_id: str) -> dict | None:
        """Get model info."""
        return self.registry.get(repo_id)

    async def delete_model(self, repo_id: str, filename: str) -> None:
        """Delete a model file."""
        record = self.registry.get(repo_id)
        if not record:
            raise ModelNotFoundError(f"Model {repo_id} not found")
        if filename not in record.get("files", {}):
            raise ModelNotFoundError(f"File {filename} not found in {repo_id}")
        path = Path(record["files"][filename]["local_path"])
        if path.exists():
            path.unlink()
        del record["files"][filename]
        self.registry._save()


def create_model_registry() -> ModelRegistry:
    """Create a model registry instance."""
    return ModelRegistry()
