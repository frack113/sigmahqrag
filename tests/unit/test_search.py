"""Tests for search module."""


import pytest


class TestSearchEngine:
    """Test SearchEngine class."""

    def test_init_defaults(self):
        """Test default initialization."""
        from sigmahqrag.rag.search import SearchEngine

        engine = SearchEngine()
        assert engine.collection_name == "sigma_rules"
        assert engine.top_k == 10
        assert engine.similarity_threshold == 0.7

    def test_init_custom(self):
        """Test custom initialization."""
        from sigmahqrag.rag.search import SearchEngine

        engine = SearchEngine(collection_name="custom", top_k=5)
        assert engine.collection_name == "custom"
        assert engine.top_k == 5


class TestSearch:
    """Test search function."""

    @pytest.mark.asyncio
    async def test_empty_query(self):
        """Test search with empty query."""
        from sigmahqrag.rag.search import search

        result = await search("")
        assert result == []


class TestFormatSearchResult:
    """Test format_search_result function."""

    def test_basic_format(self):
        """Test basic result formatting."""
        from sigmahqrag.rag.search import format_search_result

        result = {
            "text": "Test rule",
            "score": 0.85,
            "metadata": {"file_path": "test.yaml", "line_start": 10},
        }
        formatted = format_search_result(result)
        assert formatted["text"] == "Test rule"
        assert formatted["score"] == 0.85
        assert formatted["file_path"] == "test.yaml"
        assert formatted["line_number"] == 10

    def test_missing_metadata(self):
        """Test formatting with missing metadata."""
        from sigmahqrag.rag.search import format_search_result

        result = {"text": "Test", "score": 0.5, "metadata": {}}
        formatted = format_search_result(result)
        assert formatted["file_path"] == ""
        assert formatted["line_number"] == ""


class TestGetCitation:
    """Test get_citation function."""

    def test_full_citation(self):
        """Test citation with both path and line."""
        from sigmahqrag.rag.search import get_citation

        result = {"metadata": {"file_path": "test.yaml", "line_start": 42}}
        citation = get_citation(result)
        assert citation == "test.yaml:42"

    def test_missing_path(self):
        """Test citation with missing path."""
        from sigmahqrag.rag.search import get_citation

        result = {"metadata": {"line_start": 10}}
        citation = get_citation(result)
        assert citation == ""

    def test_missing_line(self):
        """Test citation with missing line."""
        from sigmahqrag.rag.search import get_citation

        result = {"metadata": {"file_path": "test.yaml"}}
        citation = get_citation(result)
        assert citation == ""
