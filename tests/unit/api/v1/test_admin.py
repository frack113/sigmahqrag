"""Tests for admin API routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    """Create test client for the app."""
    from src.main import create_app

    app = create_app()
    return TestClient(app)


class TestOrchestrationHealthEndpoint:
    """Tests for GET /api/v1/orchestration/backend endpoint."""

    def test_health_endpoint_returns_services(
        self,
        client: TestClient,
    ) -> None:
        """Given services are running When GET /api/v1/orchestration/backend Then returns service statuses."""
        with patch(
            "src.api.v1.system.orchestration.check_service_health", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = {
                "llama_cpp": {"status": "active", "port": 8080, "version": "v1.0.0"},
                "qdrant": {"status": "active", "port": 6333, "version": "v1.0.0"},
            }

            response = client.get("/api/v1/orchestration/backend")

            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "services" in data["data"]

    def test_health_endpoint_with_inactive_service(
        self,
        client: TestClient,
    ) -> None:
        """Given one stopped service When GET /api/v1/orchestration/backend Then returns all statuses."""
        with patch(
            "src.api.v1.system.orchestration.check_service_health", new_callable=AsyncMock
        ) as mock_check:
            mock_check.return_value = {
                "llama_cpp": {"status": "inactive", "port": 8080, "version": "v1.0.0"},
                "qdrant": {"status": "active", "port": 6333, "version": "v1.0.0"},
            }

            response = client.get("/api/v1/orchestration/backend")

            assert response.status_code == 200
            data = response.json()
            assert len(data["data"]["services"]) == 2
