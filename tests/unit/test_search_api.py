"""Tests for search API endpoint."""

from unittest.mock import AsyncMock, patch

import pytest


class TestSearchAPI:
    """Test search API endpoint."""

    @pytest.mark.asyncio
    async def test_search_empty_query(self):
        """Test search with empty query returns empty response."""
        from src.api.routes.search import search_rules
        from src.schemas.search import SearchRequest

        request = SearchRequest(query="", limit=10)
        response = await search_rules(request)

        assert response.data == []
        assert response.meta["count"] == 0
        assert response.meta["error"] is None

    @pytest.mark.asyncio
    async def test_search_whitespace_query(self):
        """Test search with whitespace only returns empty response."""
        from src.api.routes.search import search_rules
        from src.schemas.search import SearchRequest

        request = SearchRequest(query="   ", limit=10)
        response = await search_rules(request)

        assert response.data == []
        assert response.meta["count"] == 0

    @pytest.mark.asyncio
    async def test_search_returns_citation(self):
        """Test search returns formatted citation."""
        from src.api.routes.search import search_rules
        from src.rag.search import SearchEngine
        from src.schemas.search import SearchRequest

        with patch.object(SearchEngine, "search", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = [
                {
                    "text": "test rule content",
                    "score": 0.85,
                    "metadata": {
                        "title": "Test Rule",
                        "description": "A test rule",
                        "file_path": "rules/test.yaml",
                        "line_start": 10,
                    },
                }
            ]

            request = SearchRequest(query="test", limit=10)
            response = await search_rules(request)

            assert len(response.data) == 1
            assert response.data[0]["citation"] == "rules/test.yaml:10"

    @pytest.mark.asyncio
    async def test_search_timeout_raises_exception(self):
        """Test search timeout raises HTTPException."""
        from fastapi.exceptions import HTTPException

        from src.api.routes.search import search_rules
        from src.rag.search import SearchEngine
        from src.schemas.search import SearchRequest

        with patch.object(SearchEngine, "search", new_callable=AsyncMock) as mock_search:

            mock_search.side_effect = TimeoutError()

            request = SearchRequest(query="test", limit=10)

            with pytest.raises(HTTPException) as exc_info:
                await search_rules(request)

            assert exc_info.value.status_code == 504


class TestSearchResultSchema:
    """Test search result schema."""

    def test_search_result_defaults(self):
        """Test SearchResult has correct defaults."""
        from src.api.routes.search import SearchResult

        result = SearchResult()
        assert result.title == ""
        assert result.description == ""
        assert result.score == 0.0
        assert result.citation == ""
