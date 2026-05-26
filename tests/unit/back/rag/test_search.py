"""Tests for RAG search functionality."""

import pytest

from src.back.rag.search import SearchEngine, format_search_result, get_citation


class TestSearchEngine:
    def test_init_defaults(self) -> None:
        engine = SearchEngine()
        assert engine.collection_name == "sigmaref"
        assert engine.top_k == 15
        assert engine.similarity_threshold == 0.0

    def test_init_custom(self) -> None:
        engine = SearchEngine(collection_name="custom", top_k=5, similarity_threshold=0.5)
        assert engine.collection_name == "custom"
        assert engine.top_k == 5
        assert engine.similarity_threshold == 0.5

    def test_format_result_delegates(self) -> None:
        engine = SearchEngine()
        raw = {"text": "test", "score": 0.9, "metadata": {"file_path": "f.yaml", "line_start": 1}}
        result = engine.format_result(raw)
        assert result["text"] == "test"

    def test_get_citation_delegates(self) -> None:
        engine = SearchEngine()
        result = engine.get_citation({"metadata": {"file_path": "f.yaml", "line_start": "5"}})
        assert result == "f.yaml:5"


class TestSearch:
    @pytest.mark.asyncio
    async def test_empty_query(self) -> None:
        from src.back.rag.search import search

        result = await search("")
        assert result == []


class TestFormatSearchResult:
    def test_basic_formatting(self) -> None:
        result = format_search_result(
            {
                "text": "some rule text",
                "score": 0.95,
                "metadata": {"file_path": "/path/to/rule.yaml", "line_start": 10},
            }
        )
        assert result["text"] == "some rule text"
        assert result["score"] == 0.95
        assert result["file_path"] == "/path/to/rule.yaml"
        assert result["line_number"] == 10

    def test_empty_metadata(self) -> None:
        result = format_search_result({"text": "text", "score": 0.0, "metadata": {}})
        assert result["file_path"] == ""
        assert result["line_number"] == ""


class TestGetCitation:
    def test_with_file_and_line(self) -> None:
        result = get_citation({"metadata": {"file_path": "rules/test.yaml", "line_start": "15"}})
        assert result == "rules/test.yaml:15"

    def test_with_integer_line(self) -> None:
        result = get_citation({"metadata": {"file_path": "rules/test.yaml", "line_start": 15}})
        assert result == "rules/test.yaml:15"

    def test_missing_file(self) -> None:
        result = get_citation({"metadata": {"line_start": "15"}})
        assert result == ""

    def test_missing_line(self) -> None:
        result = get_citation({"metadata": {"file_path": "rules/test.yaml"}})
        assert result == ""

    def test_empty_metadata(self) -> None:
        result = get_citation({"metadata": {}})
        assert result == ""

    def test_no_metadata(self) -> None:
        result = get_citation({})
        assert result == ""
