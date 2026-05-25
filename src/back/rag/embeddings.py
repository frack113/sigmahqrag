"""Embedding generation for RAG pipeline."""

from __future__ import annotations

import logging
import os
from typing import Any

from llama_index.core.schema import Document

from src.back.qdrant.storage import store_embeddings as _store_embeddings
from src.shared import EMBEDDINGS_DIR

logger = logging.getLogger(__name__)

BATCH_SIZE = 32
EMBEDDING_DIM = 384

_embed_model: Any | None = None


def _check_hf_available() -> bool:
    """Check if HuggingFace Hub is accessible."""
    try:
        import httpx

        response = httpx.get("https://huggingface.co", timeout=5)
        return bool(response.status_code == 200)
    except Exception:
        return False


def get_embedding_model() -> Any:
    """Get the embedding model (singleton).

    Uses local GGUF model from models/embeddings/ or
    llama.cpp server embeddings endpoint.
    For air-gapped environments, only local GGUF models are supported.
    """
    global _embed_model

    if _embed_model is not None:
        return _embed_model

    from llama_index.embeddings.huggingface import HuggingFaceEmbedding

    embeddings_dir = EMBEDDINGS_DIR
    model_path = None

    if embeddings_dir.exists():
        gguf_files = list(embeddings_dir.glob("*.gguf"))
        if gguf_files:
            model_path = str(gguf_files[0])

    env_mode = os.environ.get("SIGMA_RAG_EMBED_MODEL", "").lower()

    if env_mode == "huggingface":
        logger.info("Using HuggingFace Hub for embeddings (SIGMA_RAG_EMBED_MODEL=huggingface)")
        _embed_model = HuggingFaceEmbedding(
            model_name="intfloat/multilingual-e5-small",
            embed_batch_size=BATCH_SIZE,
        )
        return _embed_model

    if model_path:
        logger.info(f"Using local GGUF model: {model_path}")
        _embed_model = HuggingFaceEmbedding(
            model_name=model_path,
            embed_batch_size=BATCH_SIZE,
        )
        return _embed_model

    if env_mode == "local":
        raise OSError("SIGMA_RAG_EMBED_MODEL=local but no GGUF model found in models/embeddings/")

    if _check_hf_available():
        logger.info("No local GGUF found, falling back to HuggingFace Hub")
        _embed_model = HuggingFaceEmbedding(
            model_name="intfloat/multilingual-e5-small",
            embed_batch_size=BATCH_SIZE,
        )
        return _embed_model

    raise OSError(
        "Air-gapped environment: no GGUF model in models/embeddings/ and HF Hub unreachable. "
        "Set SIGMA_RAG_EMBED_MODEL=local or provide a GGUF model."
    )


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
        embeddings = await embed_model.aembed_documents([doc.text for doc in documents])
        return list(embeddings)
    except Exception as e:
        logger.error(f"Failed to generate embeddings: {e}")
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
        vector_size=EMBEDDING_DIM,
    )


class EmbeddingGenerator:
    """Generate embeddings for RAG pipeline."""

    def __init__(
        self,
        batch_size: int = BATCH_SIZE,
        embedding_dim: int = EMBEDDING_DIM,
    ) -> None:
        """Initialize embedding generator."""
        self.batch_size = batch_size
        self.embedding_dim = embedding_dim
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
