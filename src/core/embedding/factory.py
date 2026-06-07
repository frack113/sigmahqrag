"""Embedding generation for RAG pipeline."""

from __future__ import annotations

import logging
import threading
from typing import Any

from llama_index.core.schema import Document

from src.back.database import DatabaseService
from src.back.qdrant.storage import store_embeddings as _store_embeddings
from src.core.pipeline.ingestion import DEFAULT_MODEL, get_embedding_dimension

logger = logging.getLogger(__name__)

BATCH_SIZE = 32

_embed_model: Any | None = None
_embed_model_lock = threading.Lock()


def reset_embedding_model() -> None:
    """Reset the cached embedding model singleton.

    Call this after changing the model config via set_embedding_config()
    so the next get_embedding_model() call loads the new model.
    """
    global _embed_model
    with _embed_model_lock:
        _embed_model = None


def get_embedding_model() -> Any:
    """Get the embedding model singleton, using the DuckDB config."""
    global _embed_model

    if _embed_model is not None:
        return _embed_model

    with _embed_model_lock:
        if _embed_model is not None:
            return _embed_model

        from src.core.pipeline.ingestion import build_embed_model

        config_data = DatabaseService.get_instance().get_embedding_config()
        model_name = config_data.get("model") or DEFAULT_MODEL
        _embed_model = build_embed_model(model_name)
    return _embed_model


async def embed_documents(documents: list[Document]) -> list[list[float]]:
    """Generate embeddings for documents.

    Args:
        documents: List of LlamaIndex Documents

    Returns:
        List of embedding vectors (384-dimensional)
    """
    if not documents:
        return []

    try:
        embed_model = get_embedding_model()
        texts = [doc.text for doc in documents if doc.text]
        if not texts:
            return []
        batch = embed_model.get_text_embedding_batch(texts)
        return [list(emb) for emb in batch if emb]
    except Exception as e:
        logger.error("Failed to generate embeddings: %s", e)
        return []


async def store_embeddings(
    documents: list[Document],
    embeddings: list[list[float]],
    collection_name: str = "sigmaref",
) -> bool:
    """Store embeddings in Qdrant.

    Async by design — callers in FastAPI handlers run in an event loop
    already, so the previous ``asyncio.run`` wrapper crashed with
    ``RuntimeError: asyncio.run() cannot be called from a running event
    loop`` the moment this was invoked from an API route.
    """
    texts = [doc.text for doc in documents]
    metadata = [doc.metadata for doc in documents]

    return await _store_embeddings(
        embeddings=embeddings,
        documents=texts,
        metadata=metadata,
        collection_name=collection_name,
        vector_size=get_embedding_dimension(),
    )


class EmbeddingGenerator:
    """Generate embeddings for RAG pipeline."""

    def __init__(
        self,
        batch_size: int = BATCH_SIZE,
        embedding_dim: int | None = None,
    ) -> None:
        """Initialize embedding generator."""
        self.batch_size = batch_size
        self.embedding_dim = embedding_dim or get_embedding_dimension()
        self._embed_model: Any | None = None

    def _get_embed_model(self) -> Any:
        """Get or create embedding model."""
        if self._embed_model is None:
            self._embed_model = get_embedding_model()
        return self._embed_model

    async def generate(self, documents: list[Document]) -> list[list[float]]:
        """Generate embeddings for documents."""
        return await embed_documents(documents)

    async def store(
        self,
        documents: list[Document],
        embeddings: list[list[float]],
    ) -> bool:
        """Store embeddings in Qdrant."""
        return await store_embeddings(documents, embeddings)
