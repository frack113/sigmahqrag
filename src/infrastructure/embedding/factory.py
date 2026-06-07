"""Embedding provider factory."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from src.config.settings import get_config
from src.infrastructure.database import DatabaseService

logger = logging.getLogger(__name__)


def create_embedding_provider(model_name: str | None = None) -> Any:
    """Create an embedding provider based on configuration.

    Args:
        model_name: Optional model name to use. If None, reads from DuckDB config.

    Returns:
        Configured EmbeddingProvider instance.

    Raises:
        ValueError: If no model is configured and none provided.
    """
    if model_name is None:
        config_data = DatabaseService.get_instance().get_embedding_config()
        model_name = config_data.get("model") or "intfloat/multilingual-e5-small"

    local_path = Path(get_config().embeddings_dir) / model_name
    resolved_model = str(local_path) if local_path.exists() else model_name

    logger.info("Creating HuggingFace embedding provider for model: %s", resolved_model)

    from src.infrastructure.embedding.base import HuggingFaceEmbeddingProvider

    return HuggingFaceEmbeddingProvider(model_name=resolved_model, device="cpu")


__all__ = ["create_embedding_provider"]
