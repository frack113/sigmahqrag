"""Tests for retrieval quality metrics."""

from __future__ import annotations

import pytest

from src.core.search.eval.metrics import (
    aggregate_metrics,
    average_precision,
    context_precision,
    context_recall,
    evaluate_query,
    mean_reciprocal_rank,
    precision_at_k,
    recall_at_k,
)


class TestRecallAtK:
    def test_perfect_recall(self) -> None:
        assert recall_at_k(["d1", "d2", "d3"], ["d1", "d2"]) == 1.0

    def test_partial_recall(self) -> None:
        assert recall_at_k(["d1", "d4"], ["d1", "d2"]) == 0.5

    def test_no_hits(self) -> None:
        assert recall_at_k(["d4", "d5"], ["d1", "d2"]) == 0.0

    def test_k_cutoff(self) -> None:
        # d1, d2 in top-2, 3 relevant docs total -> 2/3
        assert recall_at_k(["d1", "d2", "d3", "d4"], ["d1", "d2", "d3"], k=2) == pytest.approx(
            2.0 / 3
        )

    def test_empty_relevant(self) -> None:
        assert recall_at_k(["d1"], []) == 0.0

    def test_empty_retrieved(self) -> None:
        assert recall_at_k([], ["d1"]) == 0.0


class TestPrecisionAtK:
    def test_perfect_precision(self) -> None:
        assert precision_at_k(["d1", "d2"], ["d1", "d2"]) == 1.0

    def test_partial_precision(self) -> None:
        assert precision_at_k(["d1", "d3"], ["d1", "d2"]) == 0.5

    def test_no_hits(self) -> None:
        assert precision_at_k(["d3", "d4"], ["d1", "d2"]) == 0.0

    def test_k_cutoff(self) -> None:
        assert precision_at_k(["d1", "d2", "d3"], ["d1"], k=2) == 0.5

    def test_empty(self) -> None:
        assert precision_at_k([], ["d1"]) == 0.0


class TestMeanReciprocalRank:
    def test_first_rank(self) -> None:
        assert mean_reciprocal_rank(["d1", "d2"], ["d1"]) == 1.0

    def test_second_rank(self) -> None:
        assert mean_reciprocal_rank(["d2", "d1"], ["d1"]) == 0.5

    def test_no_hit(self) -> None:
        assert mean_reciprocal_rank(["d3", "d4"], ["d1"]) == 0.0

    def test_multiple_relevant(self) -> None:
        assert mean_reciprocal_rank(["d1", "d2", "d3"], ["d1", "d2"]) == 1.0


class TestAveragePrecision:
    def test_perfect(self) -> None:
        assert average_precision(["d1", "d2"], ["d1", "d2"]) == 1.0

    def test_partial(self) -> None:
        # d1 at rank 1, d2 at rank 3 -> AP = (1/1 + 2/3) / 2 = 5/6
        assert average_precision(["d1", "d3", "d2"], ["d1", "d2"]) == pytest.approx(5 / 6)

    def test_no_hits(self) -> None:
        assert average_precision(["d3", "d4"], ["d1", "d2"]) == 0.0

    def test_empty_relevant(self) -> None:
        assert average_precision(["d1"], []) == 0.0


class TestContextPrecision:
    def test_perfect(self) -> None:
        assert context_precision(["d1", "d2"], ["d1", "d2"]) > 0

    def test_no_hits(self) -> None:
        assert context_precision(["d3", "d4"], ["d1"]) == 0.0

    def test_empty(self) -> None:
        assert context_precision([], ["d1"]) == 0.0
        assert context_precision(["d1"], []) == 0.0


class TestContextRecall:
    def test_perfect_recall(self) -> None:
        assert context_recall(["d1", "d2", "d3"], ["d1", "d2"]) == 1.0

    def test_partial_recall(self) -> None:
        assert context_recall(["d1"], ["d1", "d2"]) == 0.5

    def test_no_recall(self) -> None:
        assert context_recall(["d3"], ["d1", "d2"]) == 0.0

    def test_empty_relevant(self) -> None:
        assert context_recall(["d1"], []) == 0.0


class TestEvaluateQuery:
    def test_returns_all_metrics(self) -> None:
        metrics = evaluate_query(["d1", "d2"], ["d1", "d2"])
        assert "recall_at_k" in metrics
        assert "precision_at_k" in metrics
        assert "mrr" in metrics
        assert "average_precision" in metrics
        assert "context_precision" in metrics
        assert "context_recall" in metrics

    def test_with_k_cutoff(self) -> None:
        metrics = evaluate_query(["d1", "d2", "d3", "d4"], ["d1", "d2", "d3"], k=2)
        assert metrics["recall_at_k"] == pytest.approx(2.0 / 3)
        assert metrics["precision_at_k"] == 1.0


class TestAggregateMetrics:
    def test_aggregate(self) -> None:
        lists = [
            {"recall_at_k": 1.0, "mrr": 1.0},
            {"recall_at_k": 0.5, "mrr": 0.5},
        ]
        agg = aggregate_metrics(lists)
        assert agg["recall_at_k"] == pytest.approx(0.75)
        assert agg["mrr"] == pytest.approx(0.75)

    def test_empty(self) -> None:
        assert aggregate_metrics([]) == {}
