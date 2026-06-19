"""Global embedding model configuration — reads from models table (single source of truth)."""

from __future__ import annotations

from src.infrastructure.database import DatabaseService

DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"


def get_embedding_config() -> dict:
    """Get the active embedding model name from the models table."""
    db = DatabaseService.get_instance()
    model_name = db.get_active_embedding_model_name()
    return {"model": model_name or DEFAULT_EMBEDDING_MODEL}


def set_embedding_config(model: str) -> None:
    """No-op: embedding config is now managed via the models table."""
