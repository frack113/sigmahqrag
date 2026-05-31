"""Search functionality for RAG pipeline."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.back.database import DatabaseService
from src.back.qdrant.client import get_qdrant_client
from src.back.rag.ingestion import build_embed_model, DEFAULT_MODEL

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 15
SIMILARITY_THRESHOLD = 0.0


_async_embed_model: Any | None = None


def _get_search_embed_model() -> Any:
    global _async_embed_model
    if _async_embed_model is None:
        config_data = DatabaseService.get_instance().get_embedding_config()
        model_name = config_data.get("model") or DEFAULT_MODEL
        _async_embed_model = build_embed_model(model_name)
    return _async_embed_model


DEFAULT_COLLECTIONS = ["sigma_rules", "sigma_docs", "sigma_spec"]


async def search(
    query: str,
    collection_name: str = "sigma_docs",
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
    """Search engine for multi-collection Sigma RAG."""

    def __init__(
        self,
        collection_names: list[str] | None = None,
        top_k: int = DEFAULT_TOP_K,
        similarity_threshold: float = SIMILARITY_THRESHOLD,
    ) -> None:
        """Initialize search engine.

        Args:
            collection_names: List of Qdrant collections to search.
                Defaults to [sigma_rules, sigma_docs, sigma_spec].
            top_k: Number of results per collection.
            similarity_threshold: Minimum similarity score.
        """
        self.collection_names = collection_names or list(DEFAULT_COLLECTIONS)
        self.top_k = top_k
        self.similarity_threshold = similarity_threshold

    async def search(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        """Search across all configured collections and fuse results with RRF.

        Searches each collection in parallel, then fuses ranked lists
        using Reciprocal Rank Fusion (RRF, k=60).
        """
        limit = top_k if top_k is not None else self.top_k
        per_collection_k = max(limit * 2, 10)

        tasks = [
            search(
                query=query,
                collection_name=col,
                top_k=per_collection_k,
                similarity_threshold=self.similarity_threshold,
            )
            for col in self.collection_names
        ]
        all_results = await asyncio.gather(*tasks)

        rrf_scores: dict[int, dict[str, Any]] = {}
        for col_results in all_results:
            for rank, result in enumerate(col_results, start=1):
                rrf_score = 1.0 / (60 + rank)
                result_id = id(result)
                if result_id not in rrf_scores:
                    result["rrf_score"] = rrf_score
                    rrf_scores[result_id] = result
                else:
                    rrf_scores[result_id]["rrf_score"] += rrf_score

        fused = sorted(rrf_scores.values(), key=lambda r: r["rrf_score"], reverse=True)
        return fused[:limit]

    async def search_collection(
        self, query: str, collection_name: str, top_k: int | None = None
    ) -> list[dict[str, Any]]:
        """Search a single specific collection."""
        limit = top_k if top_k is not None else self.top_k
        return await search(
            query=query,
            collection_name=collection_name,
            top_k=limit,
            similarity_threshold=self.similarity_threshold,
        )

    def format_result(self, result: dict[str, Any]) -> dict[str, Any]:
        """Format search result."""
        return format_search_result(result)

    def get_citation(self, result: dict[str, Any]) -> str:
        """Get citation for result."""
        return get_citation(result)
