"""Global embedding model configuration management."""

from __future__ import annotations

import logging

from src.back.database import DatabaseService

logger = logging.getLogger(__name__)


class EmbeddingTypeConfig:
    """Manages the single global embedding config via DuckDB.

    Replaced per-type mapping (doc_type -> {model, chunk_size, ...}) with
    one simple global model setting used by all ingestion pipelines.
    """

    def load(self) -> dict:
        """Load the current global config. Returns {} if missing."""
        db = DatabaseService.get_instance()
        return db.get_embedding_config()

    def save(self, data: dict) -> bool:
        """Save config — stores the global model name."""
        db = DatabaseService.get_instance()
        try:
            model = (data.get("model") or "").strip()
            if not model:
                db.delete_embedding_config()
            else:
                db.set_embedding_config(model)
            return True
        except Exception as e:
            logger.error(f"Failed to save embedding config: {e}")
            return False

    def update_type(self, _type_key: str, body: dict) -> dict | None:
        """Update the global model (second arg kept for backward compat with old callers)."""
        db = DatabaseService.get_instance()
        model = (body.get("model") or "").strip()
        if not model:
            db.delete_embedding_config()
        else:
            db.set_embedding_config(model)
        return self.load()
