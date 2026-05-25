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


class TestAdminHealthEndpoint:
    """Tests for GET /admin/health endpoint."""

    def test_health_endpoint_returns_services(
        self,
        client: TestClient,
    ) -> None:
        """Given services are running When GET /admin/health Then returns service statuses."""
        with patch(
            "src.back.backend.services.health_check.HealthCheckService"
        ) as mock_service_class:
            mock_instance = AsyncMock()
            mock_instance.check_all.return_value = {
                "llamacpp": {"status": "active", "url": "http://localhost:8080"},
                "qdrant": {"status": "ok", "host": "localhost:6333"},
                "timestamp": 1234567890.0,
            }
            mock_service_class.return_value = mock_instance

            response = client.get("/admin/health")

            assert response.status_code == 200
            data = response.json()
            assert "services" in data

    def test_health_endpoint_with_inactive_service(
        self,
        client: TestClient,
    ) -> None:
        """Given one stopped service When GET /admin/health Then returns all statuses."""
        with patch(
            "src.back.backend.services.health_check.HealthCheckService"
        ) as mock_service_class:
            mock_instance = AsyncMock()
            mock_instance.check_all.return_value = {
                "llamacpp": {"status": "error", "url": "http://localhost:8080"},
                "qdrant": {"status": "ok", "host": "localhost:6333"},
                "timestamp": 1234567890.0,
            }
            mock_service_class.return_value = mock_instance

            response = client.get("/admin/health")

            assert response.status_code == 200
            data = response.json()
            assert len(data["services"]) == 2
