"""
Configuration Service - Simplified for Gradio Native Integration

Uses data/config.json as the single source of truth.
No fallbacks or DEFAULT_* values - all settings come from config.json.
Requires data/config.json to exist at startup.
"""

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
    Configuration service reading directly from data/config.json.

    Features:
    - Single source of truth: data/config.json
    - No fallback defaults - all values from config
    - Repository management via the repositories array in config

    Note: All configuration must come from data/config.json.
    Missing required configuration will cause errors at startup.
    """

    def __init__(self, config_path: str | Path | None = None):
        """Initialize with config path (defaults to data/config.json)."""
        from src.shared.config_manager import create_config_manager

        self.config_manager = create_config_manager(config_path)

    def get_repositories(self) -> list[RepositoryConfig]:
        """Get repository configurations from config.json."""
        repos_data = self.config_manager.get("repositories", [])

        if not isinstance(repos_data, list):
            return []

        return [
            RepositoryConfig.from_dict(repo) for repo in repos_data if isinstance(repo, dict)
        ]

    def get_llm_config(self) -> dict[str, Any]:
        """Get LLM configuration from config.json."""
        llm_config = self.config_manager.get("llm", {})
        return llm_config or {}

    def get_network_config(self) -> dict[str, Any]:
        """Get network configuration from config.json."""
        network_config = self.config_manager.get("network", {})
        return network_config or {}

    def get_ui_config(self) -> dict[str, Any]:
        """Get UI/CSS configuration from config.json."""
        ui_config = self.config_manager.get("ui_css", {})
        return ui_config or {}

    def get_config_for_repositories(self) -> list[dict[str, Any]]:
        """Get repositories in format suitable for DataService operations."""
        return self.config_manager.get("repositories", [])

    def cleanup(self):
        """Clean up resources."""
        pass
