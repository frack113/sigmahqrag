"""Vector store client using Qdrant backend."""

from __future__ import annotations

from typing import Any

from src.infrastructure.vectorstore import QdrantService


class VectorStoreClient:
    """Client for vector store using Qdrant backend."""

    def __init__(
        self,
        collection_name: str = "sigmaref",
        host: str = "localhost",
        port: int = 6333,
    ) -> None:
        """Initialize the client."""
        self.service = QdrantService(
            collection_name=collection_name,
            host=host,
            port=port,
        )

    async def search(
        self,
        query_embedding: list[float],
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Search vectors."""
        await self.service.initialize()
        return await self.service.search(query_embedding, top_k=limit)

    async def add(
        self,
        embeddings: list[list[float]],
        documents: list[dict[str, Any]],
    ) -> None:
        """Add vectors."""
        await self.service.initialize()
        texts = [d.get("text", "") for d in documents]
        metadata = [d.get("metadata", {}) for d in documents]
        await self.service.add_vectors(
            embeddings=embeddings,
            documents=texts,
            metadata=metadata,
        )
