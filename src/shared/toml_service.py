"""Centralized TOML file management service."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib  # type: ignore[no-redef]

try:
    import tomli_w
except ModuleNotFoundError:
    import tomli_w as tomli_w


class TOMLService:
    """Service for reading and writing TOML files."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = Path(file_path)
        self._cache: dict[str, Any] | None = None

    def load(self, use_cache: bool = True) -> dict[str, Any]:
        """Load TOML file contents.

        Args:
            use_cache: If True, cache the result in memory.

        Returns:
            Dict with TOML contents.
        """
        if use_cache and self._cache is not None:
            return self._cache

        if not self.file_path.exists():
            logger.warning(f"TOML file not found: {self.file_path}")
            return {}

        try:
            with open(self.file_path, "rb") as f:
                data = tomllib.load(f)
                if use_cache:
                    self._cache = data
                return data
        except Exception as e:
            logger.error(f"Failed to load TOML from {self.file_path}: {e}")
            return {}

    def save(self, data: dict[str, Any], invalidate_cache: bool = True) -> bool:
        """Save data to TOML file.

        Args:
            data: Dict to serialize to TOML.
            invalidate_cache: If True, clear the cache after saving.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            clean_data = _remove_none_values(data)
            with open(self.file_path, "wb") as f:
                tomli_w.dump(clean_data, f)
            if invalidate_cache:
                self._cache = None
            return True
        except Exception as e:
            logger.error(f"Failed to save TOML to {self.file_path}: {e}")
            return False

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache = None


def _remove_none_values(obj: Any) -> Any:
    """Remove None values recursively (TOML cannot serialize None)."""
    if isinstance(obj, dict):
        return {k: _remove_none_values(v) for k, v in obj.items() if v is not None}
    elif isinstance(obj, list):
        return [_remove_none_values(item) for item in obj if item is not None]
    return obj


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> None:
    """Deep merge override into base (modifies base in place)."""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value
