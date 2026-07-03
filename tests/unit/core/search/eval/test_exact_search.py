"""Tests for exact vs approximate search comparison."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.core.search.eval.exact_search import (
    SearchComparisonResult,
    _extract_doc_ids,
    compare_collection_baseline,
    compare_exact_vs_approximate,
    run_approximate_search,
    run_exact_search,
)


class TestExtractDocIds:
    def test_flat_payload(self) -> None:
        p1 = MagicMock()
        p1.payload = {"doc_id": "id1"}
        p2 = MagicMock()
        p2.payload = {"doc_id": "id2"}
        assert _extract_doc_ids([p1, p2]) == ["id1", "id2"]

    def test_file_path_fallback(self) -> None:
        p = MagicMock()
        p.payload = {"file_path": "/rules/test.yml"}
        assert _extract_doc_ids([p]) == ["/rules/test.yml"]

    def test_empty_payload(self) -> None:
        p = MagicMock()
        p.payload = {}
        assert _extract_doc_ids([p]) == []

    def test_none_payload(self) -> None:
        p = MagicMock()
        p.payload = None
        assert _extract_doc_ids([p]) == []


class TestRunExactSearch:
    def test_returns_doc_ids(self) -> None:
        mock_point = MagicMock()
        mock_point.payload = {"doc_id": "exact-1"}
        mock_client = MagicMock()
        mock_client.search.return_value = [mock_point]
        result = run_exact_search(mock_client, "sigma_rules", [0.1] * 384, limit=10)
        assert result == ["exact-1"]
        mock_client.search.assert_called_once()

    def test_empty_results(self) -> None:
        mock_client = MagicMock()
        mock_client.search.return_value = []
        result = run_exact_search(mock_client, "sigma_rules", [0.1] * 384)
        assert result == []


class TestRunApproximateSearch:
    def test_returns_doc_ids(self) -> None:
        mock_point = MagicMock()
        mock_point.payload = {"doc_id": "approx-1"}
        mock_points = MagicMock()
        mock_points.points = [mock_point]
        mock_client = MagicMock()
        mock_client.query_points.return_value = mock_points
        result = run_approximate_search(mock_client, "sigma_rules", [0.1] * 384, limit=10)
        assert result == ["approx-1"]


class TestCompareExactVsApproximate:
    def test_perfect_recall(self) -> None:
        mock_point = MagicMock()
        mock_point.payload = {"doc_id": "d1"}
        mock_client = MagicMock()
        mock_client.search.return_value = [mock_point]
        mock_points = MagicMock()
        mock_points.points = [mock_point]
        mock_client.query_points.return_value = mock_points
        result = compare_exact_vs_approximate(mock_client, "sigma_rules", [0.1] * 384)
        assert isinstance(result, SearchComparisonResult)
        assert result.recall_at_10 == 1.0

    def test_zero_recall(self) -> None:
        exact_point = MagicMock()
        exact_point.payload = {"doc_id": "d1"}
        approx_point = MagicMock()
        approx_point.payload = {"doc_id": "d99"}
        mock_client = MagicMock()
        mock_client.search.return_value = [exact_point]
        mock_points = MagicMock()
        mock_points.points = [approx_point]
        mock_client.query_points.return_value = mock_points
        result = compare_exact_vs_approximate(mock_client, "sigma_rules", [0.1] * 384)
        assert result.recall_at_10 == 0.0


class TestCompareCollectionBaseline:
    def test_single_query(self) -> None:
        mock_point = MagicMock()
        mock_point.payload = {"doc_id": "d1"}
        mock_client = MagicMock()
        mock_client.search.return_value = [mock_point]
        mock_points = MagicMock()
        mock_points.points = [mock_point]
        mock_client.query_points.return_value = mock_points
        result = compare_collection_baseline(mock_client, "sigma_rules", [[0.1] * 384])
        assert result["mean_recall_at_10"] == 1.0
        assert result["total_queries"] == 1

    def test_multiple_queries(self) -> None:
        mock_point = MagicMock()
        mock_point.payload = {"doc_id": "d1"}
        mock_client = MagicMock()
        mock_client.search.return_value = [mock_point]
        mock_points = MagicMock()
        mock_points.points = [mock_point]
        mock_client.query_points.return_value = mock_points
        result = compare_collection_baseline(mock_client, "sigma_rules", [[0.1] * 384, [0.2] * 384])
        assert result["total_queries"] == 2

    def test_empty_embeddings(self) -> None:
        mock_client = MagicMock()
        result = compare_collection_baseline(mock_client, "sigma_rules", [])
        assert result["total_queries"] == 0
        assert result["mean_recall_at_10"] == 0.0

    def test_search_failure_handled(self) -> None:
        mock_client = MagicMock()
        mock_client.search.side_effect = RuntimeError("connection lost")
        result = compare_collection_baseline(mock_client, "sigma_rules", [[0.1] * 384])
        assert result["total_queries"] == 0
