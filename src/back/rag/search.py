"""Search functionality for RAG pipeline."""

from __future__ import annotations

import logging
from typing import Any

from src.back.backend.qdrant import QdrantService
from src.back.rag.embeddings import EMBEDDING_DIM, get_embedding_model

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 10
SIMILARITY_THRESHOLD = 0.7


async def search(
    query: str,
    collection_name: str = "sigma_rules",
    top_k: int = DEFAULT_TOP_K,
    similarity_threshold: float = SIMILARITY_THRESHOLD,
) -> list[dict[str, Any]]:
    """Search for relevant documents.

    Args:
        query: Natural language query
        collection_name: Qdrant collection name
        top_k: Number of results to return
        similarity_threshold: Minimum similarity score

    Returns:
        List of search results with metadata
    """
    if not query:
        logger.warning("Empty query provided")
        return []

    try:
        service = QdrantService(
            collection_name=collection_name,
            vector_size=EMBEDDING_DIM,
        )

        is_healthy = await service.health_check()
        if not is_healthy:
            logger.warning("Qdrant service not available")
            return []

        embed_model = get_embedding_model()
        query_embedding = await embed_model.aembed_query(query)

        results = await service.search(
            query_embedding=query_embedding,
            top_k=top_k,
        )

        filtered_results = [
            r for r in results if r.get("score", 0) >= similarity_threshold
        ]

        return filtered_results

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []


def format_search_result(result: dict[str, Any]) -> dict[str, Any]:
    """Format a search result for display.

    Args:
        result: Raw search result from Qdrant

    Returns:
        Formatted result with title, description, metadata
    """
    return {
        "text": result.get("text", ""),
        "score": result.get("score", 0.0),
        "metadata": result.get("metadata", {}),
        "file_path": result.get("metadata", {}).get("file_path", ""),
        "line_number": result.get("metadata", {}).get("line_start", ""),
    }


def get_citation(result: dict[str, Any]) -> str:
    """Get citation string for a result.

    Args:
        result: Search result

    Returns:
        Citation in format "path/to/file.yaml:line"
    """
    file_path = result.get("metadata", {}).get("file_path", "")
    line_start = result.get("metadata", {}).get("line_start", "")

    if file_path and line_start:
        return f"{file_path}:{line_start}"

    return ""


class SearchEngine:
    """Search engine for Sigma rules."""

    def __init__(
        self,
        collection_name: str = "sigma_rules",
        top_k: int = DEFAULT_TOP_K,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
    ) -> None:
        """Initialize search engine."""
        self.collection_name = collection_name
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Search for relevant documents."""
        return await search(
            query=query,
            collection_name=self.collection_name,
            top_k=self.top_k,
            similarity_threshold=self.similarity_threshold,
        )

    def format_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Format search result."""
        return format_search_result(result)

    def get_citation(self, result: dict[str, Any]) -> str:
        """Get citation for result."""
        return get_citation(result)

