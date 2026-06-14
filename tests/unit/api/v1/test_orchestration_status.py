from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.system import orchestration
from src.api.v1.infrastructure import qdrant


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI test app with orchestration and qdrant routers."""
    test_app = FastAPI()
    test_app.include_router(orchestration.router)
    test_app.include_router(qdrant.router)
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestQdrantStatus:
    """Tests for GET /api/v1/qdrant/status endpoint."""

    @patch("src.api.v1.infrastructure.qdrant.check_health", new_callable=AsyncMock)
    def test_qdrant_status_returns_200_with_component_status(
        self, mock_health: AsyncMock, client: TestClient
    ) -> None:
        """Given API processes request, when GET /api/v1/qdrant/status called, then returns component statuses (FR18)."""
        mock_health.return_value = {"status": "active"}

        response = client.get("/api/v1/qdrant/status")

        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "healthy" in data
        assert "downloads" in data

    @patch("src.api.v1.infrastructure.qdrant.check_health", new_callable=AsyncMock)
    def test_qdrant_status_responds_under_500ms(
        self, mock_health: AsyncMock, client: TestClient
    ) -> None:
        """Given API processes request, when GET /api/v1/qdrant/status called, then response time <500ms (NFR5)."""
        import time

        mock_health.return_value = {"status": "active"}

        start = time.time()
        response = client.get("/api/v1/qdrant/status")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.5  # 500ms

    @patch("src.api.v1.infrastructure.qdrant.check_health", new_callable=AsyncMock)
    def test_qdrant_status_returns_structured_error_when_health_check_fails(
        self, mock_health: AsyncMock, client: TestClient
    ) -> None:
        """Given health check fails, when GET /api/v1/qdrant/status called, then returns structured JSON (FR17, NFR9)."""
        mock_health.side_effect = Exception("Connection refused")

        response = client.get("/api/v1/qdrant/status")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"] == "An internal error occurred"
