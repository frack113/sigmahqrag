"""Tests for search API endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.search import router


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


class TestSearchAPI:
    """Test search API endpoint."""

    @patch("src.api.v1.search.search_rules", new_callable=AsyncMock)
    def test_search_returns_empty_list(self, mock_search: AsyncMock, client: TestClient) -> None:
        """Test search returns empty list when no results."""
        mock_search.return_value = []

        response = client.post("/api/v1/search?query=test")

        assert response.status_code == 200
        data = response.json()
        assert data == {"rules": []}

    @patch("src.api.v1.search.search_rules", new_callable=AsyncMock)
    def test_search_returns_rules(self, mock_search: AsyncMock, client: TestClient) -> None:
        """Test search returns rule results."""
        mock_search.return_value = ["rule-001", "rule-002"]

        response = client.post("/api/v1/search?query=test&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data == {"rules": ["rule-001", "rule-002"]}

    def test_search_empty_query(self, client: TestClient) -> None:
        """Test search with empty query returns empty list."""
        response = client.post("/api/v1/search?query=")

        assert response.status_code == 200
        data = response.json()
        assert data == {"rules": []}

    @patch("src.api.v1.search.search_rules", new_callable=AsyncMock)
    def test_search_failure_returns_500(self, mock_search: AsyncMock, client: TestClient) -> None:
        """Test search failure returns 500."""
        mock_search.side_effect = Exception("Search failed")

        response = client.post("/api/v1/search?query=test")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data


class TestSearchResultSchema:
    """Test search response schema."""

    def test_response_structure(self) -> None:
        """Test response structure has rules key."""
        from src.shared.schemas.search import SearchRequest, SearchResponse

        req = SearchRequest(query="test", limit=10)
        assert req.query == "test"
        assert req.limit == 10

        resp = SearchResponse(data=[{"id": "1"}], meta={"count": 1})
        assert resp.data == [{"id": "1"}]
        assert resp.meta["count"] == 1
