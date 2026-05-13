"""Embedding type configuration management."""

from __future__ import annotations

import logging
from pathlib import Path
from tomllib import TOMLDecodeError

from src.shared.toml_service import TOMLService, deep_merge

logger = logging.getLogger(__name__)

CONFIG_FILE = Path("data/embedding.toml")


class EmbeddingTypeConfig:
    """Manages the embedding.toml config file for type-to-model mapping."""

    def __init__(self) -> None:
        self._toml = TOMLService(CONFIG_FILE)

    def load(self) -> dict:
        """Load the current config. Returns {} if missing or corrupted."""
        try:
            return self._toml.load(use_cache=False)
        except TOMLDecodeError:
            logger.warning("Failed to parse embedding config, returning empty")
            return {}

    def save(self, data: dict) -> bool:
        """Save config dict to file."""
        return self._toml.save(data)

    def update_type(self, type_key: str, body: dict) -> dict | None:
        """Update or remove a type configuration.

        Deep-merges body under type_key. If model is empty string,
        removes the type_key section entirely.
        Returns the updated full config, or None on failure.
        """
        config = self.load()
        model = (body.get("model") or "").strip()
        if not model:
            config.pop(type_key, None)
        else:
            existing = config.get(type_key)
            if not isinstance(existing, dict):
                existing = {}
            config[type_key] = existing
            deep_merge(config[type_key], body)
        if self.save(config):
            return config
        return None
