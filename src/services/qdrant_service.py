"""QdrantService - High-level Qdrant vector store wrapper using llama-index."""

from __future__ import annotations

import logging
from typing import Any

import qdrant_client
from llama_index.vector_stores.qdrant import QdrantVectorStore

logger = logging.getLogger(__name__)


class QdrantService:
    """High-level service wrapper for Qdrant vector store via llama-index."""

    def __init__(
        self,
        collection_name: str | None = None,
        vector_size: int | None = None,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        """Initialize QdrantService."""
        from src.config import get_qdrant_config

        config = get_qdrant_config()
        self.collection_name = collection_name or config.get("collection_name", "sigma_rules")
        self.vector_size = vector_size if vector_size is not None else config.get("vector_size", 384)
        self.host = host or config.get("host", "127.0.0.1")
        self.port = port if port is not None else config.get("port", 6333)
        self._client: object | None = None
        self._vector_store: object | None = None

    async def initialize(self) -> None:
        """Initialize the Qdrant client and vector store."""
        try:
            self._client = qdrant_client.QdrantClient(
                host=self.host,
                port=self.port,
            )
            self._vector_store = QdrantVectorStore(
                client=self._client,
                collection_name=self.collection_name,
            )
            logger.info(
                f"QdrantService initialized: {self.host}:{self.port}/{self.collection_name}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize Qdrant client: {e}")
            raise

    async def add_vectors(
        self,
        embeddings: list[list[float]],
        documents: list[str],
        metadata: list[dict[str, Any]] | None = None,
    ) -> None:
        """Add vectors to the collection."""
        if self._vector_store is None:
            await self.initialize()

        from llama_index.core.schema import TextNode

        nodes = [
            TextNode(text=doc, metadata=meta or {})
            for doc, meta in zip(
                documents, metadata or [{}] * len(documents), strict=True
            )
        ]

        self._vector_store.add(nodes)  # type: ignore[union-attr]
        logger.info(f"Added {len(embeddings)} vectors to {self.collection_name}")

    async def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search for similar vectors."""
        if self._vector_store is None:
            await self.initialize()

        try:
            results = self._vector_store.query(  # type: ignore[union-attr]
                query=query_embedding,
                top_k=top_k,
            )
            nodes = results.nodes
            if nodes:
                return [
                    {
                        "text": getattr(r, "text", ""),
                        "metadata": getattr(r, "metadata", {}),
                        "score": getattr(r, "score", 0.0),
                    }
                    for r in nodes
                ]
        except Exception as e:
            logger.error(f"Search failed: {e}")
        return []

    async def health_check(self) -> bool:
        """Check if service is healthy."""
        try:
            client = qdrant_client.QdrantClient(host=self.host, port=self.port)
            collections = client.get_collections()
            return collections is not None
        except Exception as e:
            logger.debug(f"Health check failed: {e}")
            return False

    async def create_collection(self) -> None:
        """Create the collection if it doesn't exist."""
        if self._vector_store is None:
            await self.initialize()

        logger.info(f"Collection {self.collection_name} ready")

    def __repr__(self) -> str:
        return f"QdrantService(collection={self.collection_name}, host={self.host}:{self.port})"
