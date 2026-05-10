"""FastAPI dependencies."""

from functools import lru_cache

from src.back.backend.huggingface import EmbeddingManager
from src.back.backend.huggingface.registry import LocalRegistry, ModelManager


@lru_cache
def get_embedding_manager() -> EmbeddingManager:
    """Get a singleton instance of the embedding manager."""
    return EmbeddingManager()


@lru_cache
def get_model_manager() -> ModelManager:
    """Get a singleton instance of the model manager."""
    from src.shared import MODELS_DIR

    registry_path = MODELS_DIR / "registry.json"
    registry = LocalRegistry(registry_path)
    return ModelManager(registry=registry)
