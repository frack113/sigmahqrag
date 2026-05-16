"""FastAPI dependencies."""

from functools import lru_cache

from src.back.models import EmbeddingManager
from src.back.models.registry import UnifiedRegistry


@lru_cache
def get_embedding_manager() -> EmbeddingManager:
    return EmbeddingManager()


@lru_cache
def get_unified_registry() -> UnifiedRegistry:
    return UnifiedRegistry()
