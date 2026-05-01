"""Tests for GET /api/v1/admin/status endpoint (Story 3.1)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.admin import router


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI test app with admin router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestGetAdminStatus:
    """Test GET /api/v1/admin/status endpoint."""

    @patch("src.api.v1.admin.check_service_health", new_callable=AsyncMock)
    def test_status_returns_200_with_component_status(
        self, mock_health: AsyncMock, client: TestClient
    ) -> None:
        """Given API processes request, when GET /status called, then returns component statuses (FR18)."""
        mock_health.return_value = {
            "llama_cpp": {"status": "active", "component": "llama.cpp"},
            "qdrant": {"status": "inactive", "component": "qdrant"},
        }

        response = client.get("/api/v1/admin/status")

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "llama_cpp" in data["data"]
        assert "qdrant" in data["data"]

    @patch("src.api.v1.admin.check_service_health", new_callable=AsyncMock)
    def test_status_responds_under_500ms(
        self, mock_health: AsyncMock, client: TestClient
    ) -> None:
        """Given API processes request, when GET /status called, then response time <500ms (NFR5)."""
        import time

        mock_health.return_value = {
            "llama_cpp": {"status": "active", "component": "llama.cpp"},
            "qdrant": {"status": "active", "component": "qdrant"},
        }

        start = time.time()
        response = client.get("/api/v1/admin/status")
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.5  # 500ms

    @patch("src.api.v1.admin.check_service_health", new_callable=AsyncMock)
    def test_status_returns_structured_error_when_service_down(
        self, mock_health: AsyncMock, client: TestClient
    ) -> None:
        """Given llama.cpp is down, when GET /status called, then returns structured JSON (FR17, NFR9)."""
        mock_health.return_value = {
            "llama_cpp": {"status": "inactive", "component": "llama.cpp"},
            "qdrant": {"status": "active", "component": "qdrant"},
        }

        response = client.get("/api/v1/admin/status")

        # Status endpoint should always return 200 with status info, not 503
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["llama_cpp"]["status"] == "inactive"
