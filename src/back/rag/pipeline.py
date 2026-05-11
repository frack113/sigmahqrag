"""RAG pipeline implementation."""

from __future__ import annotations

from typing import Any

from src.back.qdrant.storage import store_embeddings
from src.back.rag.search import SearchEngine


class RAGPipeline:
    """RAG pipeline for semantic search."""

    def __init__(self) -> None:
        """Initialize the pipeline."""
        self.search_engine = SearchEngine()
        self._initialized = False

    def initialize(self) -> None:
        """Initialize the pipeline."""
        self._initialized = True

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for similar documents."""
        return await self.search_engine.search(query, top_k=limit)

    async def index(
        self,
        embeddings: list[list[float]],
        documents: list[str],
        metadata: list[dict[str, Any]] | None = None,
        collection_name: str = "sigma_rules",
    ) -> bool:
        """Index documents."""
        return await store_embeddings(
            embeddings=embeddings,
            documents=documents,
            metadata=metadata,
            collection_name=collection_name,
        )
