"""Global embedding model configuration management — direct DB access."""

from __future__ import annotations

from src.back.database import DatabaseService


def get_embedding_config() -> dict:
    """Get the global embedding model config from DuckDB."""
    return DatabaseService.get_instance().get_embedding_config()


def set_embedding_config(model: str) -> None:
    """Set the global embedding model in DuckDB and reset cached singletons."""
    from src.core.embedding.factory import reset_embedding_model
    from src.core.search.engine import reset_search_embed_model
    from src.core.pipeline.ingestion import reset_pipeline_registry

    db = DatabaseService.get_instance()
    model = model.strip()
    if model:
        db.set_embedding_config(model)
    else:
        db.delete_embedding_config()
    reset_embedding_model()
    reset_search_embed_model()
    reset_pipeline_registry()
