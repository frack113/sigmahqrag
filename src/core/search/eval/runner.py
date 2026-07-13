"""Search evaluation runner.

Orchestrates golden set evaluation against a ``SearchEngine`` (or any
callable that returns ranked document IDs for a query).

Usage::

    evaluator = SearchEvaluator(search_engine)
    results = evaluator.run(golden_set)
    print(results.summary())
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from src.core.search.eval.golden_set import GoldenSet
from src.core.search.eval.metrics import aggregate_metrics, evaluate_query

logger = logging.getLogger(__name__)

# Type alias for a search function: (query, collection) -> list[doc_id]
SearchFn = Callable[[str, str], list[str]]


@dataclass
class QueryResult:
    """Evaluation result for a single query."""

    query_id: str
    query: str
    collection: str
    retrieved_ids: list[str]
    relevant_ids: list[str]
    metrics: dict[str, float]
    elapsed_ms: float


@dataclass
class EvaluationResults:
    """Aggregated evaluation results across all queries."""

    queries: list[QueryResult] = field(default_factory=list)
    description: str = ""

    def add(self, result: QueryResult) -> None:
        self.queries.append(result)

    @property
    def num_queries(self) -> int:
        return len(self.queries)

    def summary(self) -> dict[str, Any]:
        """Return aggregated metrics and per-collection breakdown."""
        if not self.queries:
            return {"num_queries": 0}

        per_collection: dict[str, list[dict[str, float]]] = {}
        for qr in self.queries:
            per_collection.setdefault(qr.collection, []).append(qr.metrics)

        overall = aggregate_metrics([qr.metrics for qr in self.queries])
        per_collection_agg = {
            col: aggregate_metrics(metrics_list) for col, metrics_list in per_collection.items()
        }

        return {
            "description": self.description,
            "num_queries": self.num_queries,
            "overall": overall,
            "per_collection": per_collection_agg,
        }

    def report(self) -> str:
        """Return a human-readable evaluation report."""
        summary = self.summary()
        lines = [
            "=== Search Evaluation Report ===",
            f"Queries: {summary['num_queries']}",
            f"Description: {summary.get('description', '')}",
            "",
            "--- Overall Metrics ---",
        ]
        for key, value in summary.get("overall", {}).items():
            if isinstance(value, float):
                lines.append(f"  {key}: {value:.4f}")
            else:
                lines.append(f"  {key}: {value}")

        for col, metrics in summary.get("per_collection", {}).items():
            lines.append("")
            lines.append(f"--- {col} ---")
            for key, value in metrics.items():
                if isinstance(value, float):
                    lines.append(f"  {key}: {value:.4f}")
                else:
                    lines.append(f"  {key}: {value}")

        return "\n".join(lines)


class SearchEvaluator:
    """Evaluates a search function against a golden set.

    Args:
        search_fn: Callable that takes ``(query, collection)`` and returns
            a list of document IDs in rank order.  Typically wraps
            ``SearchEngine.search()`` or ``SearchEngine.search_collection()``.
    """

    def __init__(self, search_fn: SearchFn) -> None:
        self._search_fn = search_fn

    def _search(self, query: str, collection: str) -> list[str]:
        """Execute search and extract document IDs."""
        try:
            result = self._search_fn(query, collection)
            if isinstance(result, list):
                return result
            return []
        except Exception as e:
            logger.warning("Search failed for '%s' on '%s': %s", query, collection, e)
            return []

    def evaluate_query(self, golden_query: Any) -> QueryResult:
        """Evaluate a single golden query.

        Args:
            golden_query: A ``GoldenQuery`` dataclass instance.

        Returns:
            ``QueryResult`` with metrics.
        """
        start = time.perf_counter()
        retrieved_ids = self._search(golden_query.query, golden_query.collection)
        elapsed_ms = (time.perf_counter() - start) * 1000

        metrics = evaluate_query(retrieved_ids, golden_query.relevant_doc_ids, k=golden_query.k)

        return QueryResult(
            query_id=golden_query.id,
            query=golden_query.query,
            collection=golden_query.collection,
            retrieved_ids=retrieved_ids,
            relevant_ids=golden_query.relevant_doc_ids,
            metrics=metrics,
            elapsed_ms=elapsed_ms,
        )

    def run(
        self,
        golden_set: GoldenSet,
        description: str = "",
    ) -> EvaluationResults:
        """Run evaluation across all queries in the golden set.

        Args:
            golden_set: The golden set to evaluate against.
            description: Optional description for the report.

        Returns:
            ``EvaluationResults`` with per-query and aggregated metrics.
        """
        results = EvaluationResults(description=description)
        for q in golden_set.queries:
            qr = self.evaluate_query(q)
            results.add(qr)
            logger.info(
                "  [%s] recall@%d=%.3f MRR=%.3f (%.1fms)",
                q.id,
                q.k,
                qr.metrics["recall_at_k"],
                qr.metrics["mrr"],
                qr.elapsed_ms,
            )
        return results
