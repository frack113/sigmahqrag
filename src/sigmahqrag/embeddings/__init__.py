"""Embedding model management."""

from .download import (
    DEFAULT_EMBEDDINGS_DIR,
    download_embedding_model,
    get_embedding_model_path,
    get_recommended_embedding_models,
    is_embedding_model_downloaded,
)

__all__ = [
    "DEFAULT_EMBEDDINGS_DIR",
    "download_embedding_model",
    "get_embedding_model_path",
    "get_recommended_embedding_models",
    "is_embedding_model_downloaded",
]
