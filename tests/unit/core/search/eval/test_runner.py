"""Tests for the search evaluation runner."""

from __future__ import annotations

from src.core.search.eval.golden_set import GoldenSet
from src.core.search.eval.runner import EvaluationResults, QueryResult, SearchEvaluator


def _mock_search(query: str, collection: str) -> list[str]:
    """Deterministic mock search returning fixed IDs based on query."""
    return [f"result-for-{query}"]


class TestQueryResult:
    def test_creation(self) -> None:
        qr = QueryResult(
            query_id="q001",
            query="test",
            collection="sigma_rules",
            retrieved_ids=["r1"],
            relevant_ids=["r1"],
            metrics={"recall_at_k": 1.0},
            elapsed_ms=42.0,
        )
        assert qr.query_id == "q001"
        assert qr.elapsed_ms == 42.0


class TestEvaluationResults:
    def test_empty_summary(self) -> None:
        results = EvaluationResults(description="empty")
        summary = results.summary()
        assert summary["num_queries"] == 0

    def test_add_and_summary(self) -> None:
        results = EvaluationResults(description="test")
        results.add(
            QueryResult(
                query_id="q001",
                query="q",
                collection="sigma_rules",
                retrieved_ids=["r1"],
                relevant_ids=["r1"],
                metrics={"recall_at_k": 1.0, "mrr": 1.0},
                elapsed_ms=10.0,
            )
        )
        summary = results.summary()
        assert summary["num_queries"] == 1
        assert summary["overall"]["recall_at_k"] == 1.0
        assert "sigma_rules" in summary["per_collection"]

    def test_report_format(self) -> None:
        results = EvaluationResults(description="report test")
        results.add(
            QueryResult(
                query_id="q001",
                query="q",
                collection="sigma_rules",
                retrieved_ids=["r1"],
                relevant_ids=["r1"],
                metrics={"recall_at_k": 1.0, "mrr": 1.0},
                elapsed_ms=10.0,
            )
        )
        report = results.report()
        assert "Search Evaluation Report" in report
        assert "recall_at_k" in report


class TestSearchEvaluator:
    def test_evaluate_query(self) -> None:
        evaluator = SearchEvaluator(_mock_search)
        gs = GoldenSet()
        q = gs.add("test", "sigma_rules", ["result-for-test"])
        qr = evaluator.evaluate_query(q)
        assert qr.query_id == "q0000"
        assert qr.metrics["recall_at_k"] == 1.0
        assert qr.elapsed_ms >= 0

    def test_evaluate_query_no_hit(self) -> None:
        evaluator = SearchEvaluator(_mock_search)
        gs = GoldenSet()
        q = gs.add("test", "sigma_rules", ["nonexistent"])
        qr = evaluator.evaluate_query(q)
        assert qr.metrics["recall_at_k"] == 0.0
        assert qr.metrics["mrr"] == 0.0

    def test_run_full_set(self) -> None:
        evaluator = SearchEvaluator(_mock_search)
        gs = GoldenSet(description="full test")
        gs.add("test", "sigma_rules", ["result-for-test"])
        gs.add("test2", "sigma_docs", ["result-for-test2"])
        results = evaluator.run(gs)
        assert results.num_queries == 2
        summary = results.summary()
        assert summary["num_queries"] == 2

    def test_search_failure_returns_empty(self) -> None:
        def failing_search(query: str, collection: str) -> list[str]:
            raise RuntimeError("search failed")

        evaluator = SearchEvaluator(failing_search)
        gs = GoldenSet()
        q = gs.add("test", "sigma_rules", ["doc1"])
        qr = evaluator.evaluate_query(q)
        assert qr.retrieved_ids == []
        assert qr.metrics["recall_at_k"] == 0.0

    def test_per_collection_breakdown(self) -> None:
        def multi_collection_search(query: str, collection: str) -> list[str]:
            return [f"hit-{collection}"]

        evaluator = SearchEvaluator(multi_collection_search)
        gs = GoldenSet()
        gs.add("q1", "sigma_rules", ["hit-sigma_rules"])
        gs.add("q2", "sigma_docs", ["hit-sigma_docs"])
        results = evaluator.run(gs)
        summary = results.summary()
        assert "sigma_rules" in summary["per_collection"]
        assert "sigma_docs" in summary["per_collection"]
