"""File whitelisting for repositories."""

from __future__ import annotations

import fnmatch
import logging
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

DEFAULT_PATTERNS = ("*.yml", "*.yaml", "rules/*", "rules/**/*")

CONFIG_FILENAME = ".sigmahqrag.yaml"


class WhitelistConfig:
    """Whitelist configuration for a repository."""

    def __init__(self, repo_path: Path) -> None:
        """Initialize whitelist config.

        Args:
            repo_path: Path to repository
        """
        self.repo_path = repo_path
        self.config_path = repo_path / CONFIG_FILENAME
        self._cached_patterns: tuple[str, ...] | None = None

    def get_patterns(self) -> tuple[str, ...]:
        """Get whitelist patterns.

        Returns:
            Tuple of glob patterns
        """
        if self._cached_patterns is not None:
            return self._cached_patterns

        if not self.config_path.exists():
            return DEFAULT_PATTERNS

        try:
            with open(self.config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if config and "whitelist" in config:
                patterns = tuple(config["whitelist"])
                self._cached_patterns = patterns
                return patterns

        except Exception as e:
            logger.warning(f"Failed to load whitelist config: {e}")

        return DEFAULT_PATTERNS

    def set_patterns(self, patterns: list[str]) -> dict[str, Any]:
        """Set whitelist patterns.

        Args:
            patterns: List of glob patterns

        Returns:
            Dict with save status
        """
        try:
            config = {"whitelist": patterns}

            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False)

            self._cached_patterns = tuple(patterns)

            logger.info(f"Saved whitelist config to {self.config_path}")
            return {"success": True}

        except Exception as e:
            logger.error(f"Failed to save whitelist config: {e}")
            return {"success": False, "error": str(e)}

    def invalidate_cache(self) -> None:
        """Invalidate the cached patterns."""
        self._cached_patterns = None

    def is_allowed(self, file_path: str) -> bool:
        """Check if a file path matches whitelist.

        Args:
            file_path: Relative file path

        Returns:
            True if file is allowed
        """
        patterns = self.get_patterns()
        file_name = Path(file_path).name
        rel_path = file_path

        for pattern in patterns:
            if fnmatch.fnmatch(file_name, pattern):
                return True
            if fnmatch.fnmatch(rel_path, pattern):
                return True

        return False

    def filter_files(self, file_paths: list[str]) -> list[str]:
        """Filter files based on whitelist.

        Args:
            file_paths: List of file paths

        Returns:
            List of allowed file paths
        """
        return [f for f in file_paths if self.is_allowed(f)]


def create_whitelist_config(repo_path: str | Path) -> WhitelistConfig:
    """Create whitelist config for a repository.

    Args:
        repo_path: Path to repository

    Returns:
        WhitelistConfig instance
    """
    return WhitelistConfig(Path(repo_path))
