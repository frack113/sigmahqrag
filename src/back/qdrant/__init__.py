"""Qdrant backend package."""

from __future__ import annotations

import logging
from typing import Any

import qdrant_client
from llama_index.vector_stores.qdrant import QdrantVectorStore

from .client import get_qdrant_client
from .collections import (
    create_collection,
    delete_collection,
    get_collection,
    list_collections,
)
from .health import check_health
from .storage import search, store_embeddings

logger = logging.getLogger(__name__)


def get_version() -> str | None:
    """Get current qdrant version."""
    from src.shared import get_config

    return get_config().qdrant_version


def set_version(version: str) -> None:
    """Set qdrant version."""
    from src.shared import get_config

    config = get_config()
    config.qdrant_version = version
    config.save()


def set_webui_version(version: str) -> None:
    """Set qdrant webui version."""
    from src.shared import get_config

    config = get_config()
    config.qdrant_webui_version = version
    config.save()


class QdrantVectorService:
    """High-level service wrapper for Qdrant vector store via llama-index."""

    def __init__(
        self,
        collection_name: str | None = None,
        vector_size: int | None = None,
        host: str | None = None,
        port: int | None = None,
    ) -> None:
        """Initialize QdrantVectorService."""
        from src.shared import get_config

        config = get_config()
        self.collection_name = collection_name or config.qdrant_collection_name
        self.vector_size = vector_size if vector_size is not None else config.qdrant_vector_size
        self.host = host or config.qdrant_host
        self.port = port if port is not None else config.qdrant_port
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
                f"QdrantVectorService initialized: {self.host}:{self.port}/{self.collection_name}"
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
            for doc, meta in zip(documents, metadata or [{}] * len(documents), strict=True)
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
            client = get_qdrant_client(host=self.host, port=self.port)
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


QdrantService = QdrantVectorService


__all__ = [
    "QdrantVectorService",
    "QdrantService",
    "check_health",
    "store_embeddings",
    "search",
    "get_version",
    "set_version",
    "list_collections",
    "create_collection",
    "delete_collection",
    "get_collection",
]
