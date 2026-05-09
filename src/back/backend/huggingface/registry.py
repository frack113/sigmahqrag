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


def create_model_registry() -> ModelRegistry:
    """Create a model registry instance."""
    return ModelRegistry()
