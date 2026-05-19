"""FastAPI dependencies."""

from src.back.models import EmbeddingManager
from src.back.models.registry import UnifiedRegistry


def get_embedding_manager() -> EmbeddingManager:
    return EmbeddingManager()


def get_unified_registry() -> UnifiedRegistry:
    return UnifiedRegistry()
