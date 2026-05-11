"""Tests for POST /api/v1/admin/download endpoint (Story 3.1 - RED phase)."""

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


class TestPostAdminDownload:
    """Test POST /api/v1/admin/download endpoint."""

    @patch("src.api.v1.qdrant.create_download_manager")
    @patch("src.api.v1.admin.check_service_health", new_callable=AsyncMock)
    def test_qdrant_download_returns_200_with_job_id(
        self, mock_health: AsyncMock, mock_dm: AsyncMock, client: TestClient
    ) -> None:
        """Given frontend needs to download repos, when POST /api/v1/qdrant called, then returns 200 with job_id (FR16)."""
        mock_health.return_value = {
            "llama_cpp": {"status": "active", "component": "llama.cpp"},
            "qdrant": {"status": "active", "component": "qdrant"},
        }

        # Mocking the download manager to return a dummy stream
        mock_manager = AsyncMock()
        mock_dm.return_value = mock_manager

        payload = {"action": "download_update", "payload": {"version": "latest"}}

        response = client.post(
            "/api/v1/qdrant",
            json=payload,
            headers={"X-Idempotency-Key": "key-1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data["status"]
        assert "Download initiated" in data["message"]

    @patch("src.api.v1.admin.check_service_health", new_callable=AsyncMock)
    @patch("src.api.v1.admin.start_download", new_callable=AsyncMock)
    def test_download_with_idempotency_key_returns_same_result(
        self, mock_start: AsyncMock, mock_health: AsyncMock, client: TestClient
    ) -> None:
        """Given POST called twice with same idempotency key, when headers include X-Idempotency-Key, then second call returns same result (FR20, NFR20)."""
        mock_start.return_value = {"job_id": "job-456", "status": "started"}
        mock_health.return_value = {
            "llama_cpp": {"status": "active", "component": "llama.cpp"},
            "qdrant": {"status": "active", "component": "qdrant"},
        }

        response1 = client.post(
            "/api/v1/admin/download",
            json={},
            headers={"X-Idempotency-Key": "same-key"},
        )
        response2 = client.post(
            "/api/v1/admin/download",
            json={},
            headers={"X-Idempotency-Key": "same-key"},
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response1.json()["data"]["job_id"] == response2.json()["data"]["job_id"]

    @patch("src.api.v1.admin.check_service_health", new_callable=AsyncMock)
    def test_download_returns_503_when_llama_cpp_down(
        self, mock_health: AsyncMock, client: TestClient
    ) -> None:
        """Given llama.cpp is down, when calling download endpoint, then returns structured 503 JSON (FR17, NFR9, NFR10)."""
        mock_health.return_value = {
            "llama_cpp": {"status": "inactive", "component": "llama.cpp"},
            "qdrant": {"status": "active", "component": "qdrant"},
        }

        response = client.post(
            "/api/v1/admin/download",
            json={},
        )

        assert response.status_code == 503
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == 503
        assert "llama.cpp" in data["error"]["message"].lower()

    def test_download_without_idempotency_key_processes_normally(
        self, client: TestClient
    ) -> None:
        """Given request has no idempotency key, when API receives it, then processes normally (backward compatible, NFR20)."""
        with (
            patch(
                "src.api.v1.admin.check_service_health", new_callable=AsyncMock
            ) as mock_health,
            patch(
                "src.api.v1.admin.start_download", new_callable=AsyncMock
            ) as mock_start,
        ):
            mock_start.return_value = {"job_id": "job-789", "status": "started"}
            mock_health.return_value = {
                "llama_cpp": {"status": "active", "component": "llama.cpp"},
                "qdrant": {"status": "active", "component": "qdrant"},
            }

            response = client.post(
                "/api/v1/admin/download",
                json={},
            )

            assert response.status_code == 200
            assert "data" in response.json()
            assert "job_id" in response.json()["data"]


class TestResponseTime:
    """Test response time requirements (NFR5)."""

    @patch("src.api.v1.admin.check_service_health", new_callable=AsyncMock)
    @patch("src.api.v1.admin.start_download", new_callable=AsyncMock)
    def test_download_responds_under_500ms(
        self, mock_start: AsyncMock, mock_health: AsyncMock, client: TestClient
    ) -> None:
        """Given API processes request, when llama.cpp handles it, then response time <500ms (NFR5)."""
        import time

        mock_start.return_value = {"job_id": "job-fast", "status": "started"}
        mock_health.return_value = {
            "llama_cpp": {"status": "active", "component": "llama.cpp"},
            "qdrant": {"status": "active", "component": "qdrant"},
        }

        start = time.time()
        response = client.post("/api/v1/admin/download", json={})
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 0.5  # 500ms
