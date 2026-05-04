"""Storage operations for Qdrant."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_VECTOR_SIZE = 384


async def store_embeddings(
    embeddings: list[list[float]],
    documents: list[str],
    metadata: list[dict[str, Any]] | None = None,
    collection_name: str = "sigma_rules",
    vector_size: int = DEFAULT_VECTOR_SIZE,
) -> bool:
    """Store embeddings in Qdrant.

    Args:
        embeddings: Embedding vectors
        documents: Original documents
        metadata: Optional metadata for each document
        collection_name: Qdrant collection name
        vector_size: Vector dimension

    Returns:
        True if successful
    """
    if len(documents) != len(embeddings):
        logger.error("Document count must match embedding count")
        return False

    try:
        from src.core.backend.qdrant import QdrantService

        service = QdrantService(
            collection_name=collection_name,
            vector_size=vector_size,
        )
        await service.initialize()

        await service.add_vectors(
            embeddings=embeddings,
            documents=documents,
            metadata=metadata,
        )
        return True
    except Exception as e:
        logger.error(f"Failed to store embeddings: {e}")
        return False


async def search(
    query_embedding: list[float],
    collection_name: str = "sigma_rules",
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Search for similar vectors in Qdrant.

    Args:
        query_embedding: Query vector
        collection_name: Qdrant collection name
        top_k: Number of results to return

    Returns:
        List of search results with text, metadata, and score
    """
    try:
        from src.core.backend.qdrant import QdrantService

        service = QdrantService(collection_name=collection_name)
        await service.initialize()

        return await service.search(
            query_embedding=query_embedding,
            top_k=top_k,
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []
