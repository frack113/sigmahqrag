"""FastAPI dependencies."""

from functools import lru_cache

from src.core.services.embedding import EmbeddingManager
from src.core.services.manager import ModelManager


@lru_cache
def get_embedding_manager() -> EmbeddingManager:
    """Get a singleton instance of the embedding manager."""
    return EmbeddingManager()


@lru_cache
def get_model_manager() -> ModelManager:
    """Get a singleton instance of the model manager."""
    return ModelManager()
