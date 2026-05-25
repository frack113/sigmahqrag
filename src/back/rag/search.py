"""Search functionality for RAG pipeline."""

from __future__ import annotations

import logging
from typing import Any

from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from src.back.qdrant.client import get_qdrant_client

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 15
SIMILARITY_THRESHOLD = 0.0
DEFAULT_EMBED_MODEL = "intfloat/multilingual-e5-small"


_async_embed_model: Any | None = None


def _get_search_embed_model() -> Any:
    global _async_embed_model
    if _async_embed_model is None:
        _async_embed_model = HuggingFaceEmbedding(model_name=DEFAULT_EMBED_MODEL)
    return _async_embed_model


async def search(
    query: str,
    collection_name: str = "sigmaref",
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
        client = get_qdrant_client()
        embed_model = _get_search_embed_model()
        query_embedding = await embed_model.aget_query_embedding(query)

        points = client.query_points(collection_name, query=query_embedding, limit=top_k)
        scored_points = points.points

        if not scored_points:
            return []

        results = []
        for point in scored_points:
            score = point.score if point.score else 0.0
            if score >= similarity_threshold:
                payload = point.payload or {}

                # Support both flat payload format (from JSONL injection)
                # and LlamaIndex _node_content format
                text = payload.get("text", "")
                metadata = {}

                if not text:
                    # Fallback: try _node_content format
                    node_content = payload.get("_node_content", "{}")
                    if isinstance(node_content, str):
                        import json

                        try:
                            node_data = json.loads(node_content)
                            text = node_data.get("text", "")
                            metadata = node_data.get("metadata", {})
                        except (json.JSONDecodeError, KeyError):
                            text = ""
                            metadata = payload
                    else:
                        text = node_content.get("text", "") if node_content else ""
                        metadata = node_content.get("metadata", {}) if node_content else {}

                results.append(
                    {
                        "text": text,
                        "score": score,
                        "metadata": metadata,
                    }
                )

        return results

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
        collection_name: str = "sigmaref",
        top_k: int = DEFAULT_TOP_K,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
    ) -> None:
        """Initialize search engine."""
        self.collection_name = collection_name
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    async def search(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        """Search for relevant documents."""
        limit = top_k if top_k is not None else self.top_k
        return await search(
            query=query,
            collection_name=self.collection_name,
            top_k=limit,
            similarity_threshold=self.similarity_threshold,
        )

    def format_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Format search result."""
        return format_search_result(result)

    def get_citation(self, result: dict[str, Any]) -> str:
        """Get citation for result."""
        return get_citation(result)
