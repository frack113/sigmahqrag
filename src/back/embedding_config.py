"""Embedding type configuration management."""

from __future__ import annotations

import logging

from src.back.database import DatabaseService

logger = logging.getLogger(__name__)


class EmbeddingTypeConfig:
    """Manages the embedding config via DuckDB for type-to-model mapping."""

    def load(self) -> dict:
        """Load the current config. Returns {} if missing."""
        db = DatabaseService.get_instance()
        if db is None:
            return {}
        return db.get_embedding_config()

    def save(self, data: dict) -> bool:
        """Save config dict to DuckDB."""
        db = DatabaseService.get_instance()
        if db is None:
            return False
        try:
            for doc_type, cfg in data.items():
                if isinstance(cfg, dict):
                    db.set_embedding_config(doc_type, cfg)
            return True
        except Exception as e:
            logger.error(f"Failed to save embedding config: {e}")
            return False

    def update_type(self, type_key: str, body: dict) -> dict | None:
        db = DatabaseService.get_instance()
        if db is None:
            return None
        model = (body.get("model") or "").strip()
        if not model:
            db.delete_embedding_config(type_key)
        else:
            config = self.load()
            existing = config.get(type_key)
            if not isinstance(existing, dict):
                existing = {}
            existing.update(body)
            db.set_embedding_config(type_key, existing)
        return self.load()
