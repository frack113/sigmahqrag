"""Embedding manager service (wrapper for backward compatibility)."""

from src.back.backend.huggingface import (
    EmbeddingManager,
    create_embedding_manager,
)


def create_embedding_manager_service() -> EmbeddingManager:
    """Create an EmbeddingManager instance."""
    return create_embedding_manager()
