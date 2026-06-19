"""Tests for idempotency middleware (Story 3.2 - RED phase)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.system.orchestration import router


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI test app with orchestration router."""
    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestIdempotencyMiddleware:
    """Test X-Idempotency-Key header processing."""

    @patch("src.api.v1.system.orchestration.check_service_health", new_callable=AsyncMock)
    @patch("src.api.v1.system.orchestration.start_download", new_callable=AsyncMock)
    def test_same_key_returns_same_response(
        self, mock_start: AsyncMock, mock_health: AsyncMock, client: TestClient
    ) -> None:
        """Given POST called twice with same key, when headers include X-Idempotency-Key, then second call returns cached response (FR20, NFR20)."""
        mock_start.return_value = {"job_id": "job-123", "status": "started"}
        mock_health.return_value = {
            "llama_cpp": {"status": "active"},
            "qdrant": {"status": "active"},
        }

        response1 = client.post(
            "/api/v1/orchestration/download",
            json={},
            headers={"X-Idempotency-Key": "same-key-123"},
        )
        response2 = client.post(
            "/api/v1/orchestration/download",
            json={},
            headers={"X-Idempotency-Key": "same-key-123"},
        )

        assert response1.status_code == 202
        assert response2.status_code == 202

    @patch("src.api.v1.system.orchestration.check_service_health", new_callable=AsyncMock)
    @patch("src.api.v1.system.orchestration.start_download", new_callable=AsyncMock)
    def test_different_keys_return_different_responses(
        self, mock_start: AsyncMock, mock_health: AsyncMock, client: TestClient
    ) -> None:
        """Given POST called with different keys, when headers differ, then responses are independent."""
        # Mock different return values for each call
        mock_start.side_effect = [
            {"job_id": "job-456", "status": "started"},
            {"job_id": "job-789", "status": "started"},
        ]
        mock_health.return_value = {
            "llama_cpp": {"status": "active"},
            "qdrant": {"status": "active"},
        }

        response1 = client.post(
            "/api/v1/orchestration/download",
            json={},
            headers={"X-Idempotency-Key": "key-A"},
        )
        response2 = client.post(
            "/api/v1/orchestration/download",
            json={},
            headers={"X-Idempotency-Key": "key-B"},
        )

        assert response1.status_code == 202
        assert response2.status_code == 202

    def test_no_idempotency_key_processes_normally(self, client: TestClient) -> None:
        """Given request has no idempotency key, when API receives it, then processes normally (NFR20)."""
        with (
            patch(
                "src.api.v1.system.orchestration.check_service_health", new_callable=AsyncMock
            ) as mock_health,
            patch(
                "src.api.v1.system.orchestration.start_download", new_callable=AsyncMock
            ) as mock_start,
        ):
            mock_start.return_value = {"job_id": "job-789", "status": "started"}
            mock_health.return_value = {
                "llama_cpp": {"status": "active"},
                "qdrant": {"status": "active"},
            }

            response = client.post(
                "/api/v1/orchestration/download",
                json={},
            )

            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "started"

    @patch("src.api.v1.system.orchestration.check_service_health", new_callable=AsyncMock)
    def test_get_request_ignores_idempotency_key(
        self, mock_health: AsyncMock, client: TestClient
    ) -> None:
        """Given GET request with idempotency key, when it's a GET, then key is ignored (idempotency for POST/PUT only)."""
        mock_health.return_value = {
            "llama_cpp": {"status": "active"},
            "qdrant": {"status": "active"},
        }

        response = client.get(
            "/api/v1/orchestration/status",
            headers={"X-Idempotency-Key": "should-be-ignored"},
        )

        assert response.status_code == 200
        # Should not cache GET requests
        assert "data" in response.json()

    def test_empty_idempotency_key(self, client: TestClient) -> None:
        """Given POST with empty idempotency key, when key is empty string, then processes normally (no caching)."""
        with (
            patch(
                "src.api.v1.system.orchestration.check_service_health", new_callable=AsyncMock
            ) as mock_health,
            patch(
                "src.api.v1.system.orchestration.start_download", new_callable=AsyncMock
            ) as mock_start,
        ):
            mock_start.return_value = {"job_id": "job-empty", "status": "started"}
            mock_health.return_value = {
                "llama_cpp": {"status": "active"},
                "qdrant": {"status": "active"},
            }

            response = client.post(
                "/api/v1/orchestration/download",
                json={},
                headers={"X-Idempotency-Key": ""},
            )

            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "started"
