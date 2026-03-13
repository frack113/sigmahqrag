"""
Configuration Service for Gradio Native Integration

Uses simple synchronous methods - no async wrappers needed:
- Direct JSON file operations
- Simple CRUD operations
- Gradio queue=True handles async execution
"""

import json
import os
from pathlib import Path
from typing import Any


class RepositoryConfig:
    """Repository configuration data class."""

    def __init__(
        self,
        url: str,
        branch: str,
        enabled: bool = True,
        file_extensions: list[str] | None = None,
    ):
        self.url = url
        self.branch = branch
        self.enabled = enabled
        self.file_extensions = file_extensions or []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "branch": self.branch,
            "enabled": self.enabled,
            "file_extensions": self.file_extensions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RepositoryConfig":
        """Create from dictionary."""
        return cls(
            url=data["url"],
            branch=data["branch"],
            enabled=data.get("enabled", True),
            file_extensions=data.get("file_extensions", []),
        )


class ConfigService:
    """
    Configuration service using simple synchronous methods.

    Features:
    - JSON-based configuration storage
    - Simple CRUD operations (Gradio queue=True handles async)
    - Repository management with dataclasses
    """

    def __init__(self):
        self.config_dir = Path("data")
        self.github_config_path = self.config_dir / "github.json"
        self.rag_config_path = self.config_dir / "rag_config.json"

        # Load existing configurations
        self._ensure_default_configs()

    def _ensure_default_configs(self):
        """Ensure default configuration files exist."""
        if not self.github_config_path.exists():
            self.github_config_path.parent.mkdir(parents=True, exist_ok=True)

            default_repos = [
                RepositoryConfig(
                    url="https://github.com/user/repo1.git",
                    branch="main",
                    enabled=True,
                    file_extensions=["py", "js", "ts"],
                )
            ]

            with open(self.github_config_path, "w", encoding="utf-8") as f:
                json.dump(
                    {"repositories": [r.to_dict() for r in default_repos]}, f, indent=2
                )

    def get_repositories(self) -> list[RepositoryConfig]:
        """Get repository configurations."""
        if not self.github_config_path.exists():
            return []

        try:
            with open(self.github_config_path, encoding="utf-8") as f:
                data = json.load(f)
                return [
                    RepositoryConfig.from_dict(r) for r in data.get("repositories", [])
                ]
        except Exception as e:
            print(f"Error loading repositories: {e}")
            return []

    def update_repositories(self, repos: list[RepositoryConfig]) -> bool:
        """Update repository configurations."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            data = {"repositories": [r.to_dict() for r in repos]}

            with open(self.github_config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            return True
        except Exception as e:
            print(f"Error updating repositories: {e}")
            return False

    def get_rag_config(self) -> dict[str, Any]:
        """Get RAG configuration."""
        if not self.rag_config_path.exists():
            return {
                "embedding_model": "all-MiniLM-L6-v2",
                "collection_name": "chat_collection",
                "chunk_size": 1000,
                "chunk_overlap": 200,
            }

        try:
            with open(self.rag_config_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading RAG config: {e}")
            return {
                "embedding_model": "all-MiniLM-L6-v2",
                "collection_name": "chat_collection",
                "chunk_size": 1000,
                "chunk_overlap": 200,
            }

    def update_rag_config(self, config: dict[str, Any]) -> bool:
        """Update RAG configuration."""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            with open(self.rag_config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)

            return True
        except Exception as e:
            print(f"Error updating RAG config: {e}")
            return False

    def get_server_config(self) -> dict[str, Any]:
        """Get server configuration."""

        return {
            "host": os.getenv("HOST", "0.0.0.0"),
            "port": int(os.getenv("PORT", 8002)),
            "base_url": os.getenv("LLM_BASE_URL", "http://localhost:1234"),
            "api_key": os.getenv("LLM_API_KEY", ""),
        }

    def cleanup(self):
        """Clean up resources."""
        pass
