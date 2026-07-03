"""Exact vs approximate search comparison for Qdrant collections.

Provides utilities to:
- Run dense exact search (flat scan) on a Qdrant collection
- Compare exact results against the default HNSW approximate search
- Compute recall@k of approximate search relative to exact search

This is used as a baseline (Q0.2) to determine whether HNSW parameters
need tuning — if approximate recall drops >5% below exact, ``ef`` and ``m``
should be adjusted.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from qdrant_client import QdrantClient

from src.core.search.eval.metrics import recall_at_k

logger = logging.getLogger(__name__)


@dataclass
class SearchComparisonResult:
    """Result of comparing exact vs approximate search."""

    collection: str
    query: str
    exact_ids: list[str]
    approx_ids: list[str]
    recall_at_10: float
    recall_at_20: float
    recall_at_50: float
    exact_count: int
    approx_count: int

    def summary(self) -> dict[str, Any]:
        return {
            "collection": self.collection,
            "query": self.query,
            "exact_count": self.exact_count,
            "approx_count": self.approx_count,
            "recall@10": self.recall_at_10,
            "recall@20": self.recall_at_20,
            "recall@50": self.recall_at_50,
            "approx_below_exact_threshold": self.recall_at_10 < 0.95,
        }


def _extract_doc_ids(points: list[Any]) -> list[str]:
    """Extract document IDs from Qdrant scored points."""
    ids: list[str] = []
    for point in points:
        payload = point.payload or {}
        doc_id = payload.get("doc_id") or payload.get("file_path") or payload.get("id")
        if doc_id:
            ids.append(str(doc_id))
    return ids


def run_exact_search(
    client: QdrantClient,
    collection: str,
    query_embedding: list[float],
    limit: int = 100,
) -> list[str]:
    """Run dense exact search (flat scan, no HNSW approximation).

    Uses ``search()`` with a large limit to get a near-complete result set,
    which serves as the ground truth for recall computation.

    Args:
        client: Active Qdrant client.
        collection: Collection name.
        query_embedding: Query vector.
        limit: Maximum number of results to return.

    Returns:
        List of document IDs in relevance order.
    """
    points = client.search(  # type: ignore[attr-defined]
        collection_name=collection,
        query_vector=query_embedding,
        limit=limit,
    )
    return _extract_doc_ids(points)


def run_approximate_search(
    client: QdrantClient,
    collection: str,
    query_embedding: list[float],
    limit: int = 50,
) -> list[str]:
    """Run dense approximate search (HNSW, default parameters).

    Args:
        client: Active Qdrant client.
        collection: Collection name.
        query_embedding: Query vector.
        limit: Maximum number of results to return.

    Returns:
        List of document IDs in relevance order.
    """
    points = client.query_points(
        collection_name=collection,
        query=query_embedding,
        limit=limit,
    )
    return _extract_doc_ids(points.points)


def compare_exact_vs_approximate(
    client: QdrantClient,
    collection: str,
    query_embedding: list[float],
    exact_limit: int = 100,
    approx_limit: int = 50,
    recall_threshold: float = 0.95,
) -> SearchComparisonResult:
    """Compare exact search against approximate (HNSW) search.

    Runs both searches and computes recall@k of approximate relative to exact.

    Args:
        client: Active Qdrant client.
        collection: Collection name.
        query_embedding: Query vector.
        exact_limit: Number of results for exact search.
        approx_limit: Number of results for approximate search.
        recall_threshold: If recall@10 falls below this, the result flags
            ``approx_below_exact_threshold`` as ``True``.

    Returns:
        ``SearchComparisonResult`` with recall scores at k=10, 20, 50.
    """
    exact_ids = run_exact_search(client, collection, query_embedding, limit=exact_limit)
    approx_ids = run_approximate_search(client, collection, query_embedding, limit=approx_limit)

    r10 = recall_at_k(approx_ids, exact_ids, k=10)
    r20 = recall_at_k(approx_ids, exact_ids, k=20)
    r50 = recall_at_k(approx_ids, exact_ids, k=min(50, len(exact_ids)))

    result = SearchComparisonResult(
        collection=collection,
        query="<embedding comparison>",
        exact_ids=exact_ids,
        approx_ids=approx_ids,
        recall_at_10=r10,
        recall_at_20=r20,
        recall_at_50=r50,
        exact_count=len(exact_ids),
        approx_count=len(approx_ids),
    )

    if r10 < recall_threshold:
        logger.warning(
            "Approximate search recall@10=%.3f below threshold %.2f on '%s'",
            r10,
            recall_threshold,
            collection,
        )
    else:
        logger.info(
            "Approximate search recall@10=%.3f on '%s' (OK, threshold=%.2f)",
            r10,
            collection,
            recall_threshold,
        )

    return result


def compare_collection_baseline(
    client: QdrantClient,
    collection: str,
    query_embeddings: list[list[float]],
    recall_threshold: float = 0.95,
) -> dict[str, float]:
    """Run exact vs approximate comparison across multiple queries.

    Aggregates recall@10 across all queries to produce a single baseline
    metric for the collection.

    Args:
        client: Active Qdrant client.
        collection: Collection name.
        query_embeddings: List of query vectors to test.
        recall_threshold: Threshold for flagging poor recall.

    Returns:
        Dict with aggregated metrics:
        ``mean_recall_at_10``, ``min_recall_at_10``, ``max_recall_at_10``,
        ``queries_below_threshold``.
    """
    recalls_10: list[float] = []
    below_count = 0

    for i, embedding in enumerate(query_embeddings):
        try:
            result = compare_exact_vs_approximate(
                client, collection, embedding, recall_threshold=recall_threshold
            )
            recalls_10.append(result.recall_at_10)
            if result.recall_at_10 < recall_threshold:
                below_count += 1
        except Exception as e:
            logger.warning("Comparison failed for query %d on '%s': %s", i, collection, e)

    if not recalls_10:
        return {
            "mean_recall_at_10": 0.0,
            "min_recall_at_10": 0.0,
            "max_recall_at_10": 0.0,
            "queries_below_threshold": 0,
            "total_queries": 0,
        }

    return {
        "mean_recall_at_10": sum(recalls_10) / len(recalls_10),
        "min_recall_at_10": min(recalls_10),
        "max_recall_at_10": max(recalls_10),
        "queries_below_threshold": below_count,
        "total_queries": len(query_embeddings),
    }
