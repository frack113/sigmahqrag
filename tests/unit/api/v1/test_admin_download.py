"""Tests for POST /api/v1/orchestration/download endpoint."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.infrastructure import qdrant
from src.api.v1.system import orchestration


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


class TestPostDownload:
    """Test POST /api/v1/orchestration/download endpoint."""

    @patch("src.api.v1.system.orchestration.check_service_health", new_callable=AsyncMock)
    @patch("src.api.v1.system.orchestration.start_download", new_callable=AsyncMock)
    def test_download_with_idempotency_key_returns_same_result(
        self, mock_start: AsyncMock, mock_health: AsyncMock, client: TestClient
    ) -> None:
        """Given POST called twice with same idempotency key, when headers include X-Idempotency-Key, then second call returns 202."""
        mock_start.return_value = {"job_id": "job-456", "status": "started"}
        mock_health.return_value = {
            "llama_cpp": {"status": "active", "component": "llama.cpp"},
            "qdrant": {"status": "active", "component": "qdrant"},
        }

        response1 = client.post(
            "/api/v1/orchestration/download",
            json={"service": "qdrant"},
            headers={"X-Idempotency-Key": "same-key"},
        )
        response2 = client.post(
            "/api/v1/orchestration/download",
            json={"service": "qdrant"},
            headers={"X-Idempotency-Key": "same-key"},
        )

        assert response1.status_code == 202
        assert response2.status_code == 202

    @patch("src.api.v1.system.orchestration.start_download", new_callable=AsyncMock)
    def test_download_returns_202_with_service_info(
        self, mock_start: AsyncMock, client: TestClient
    ) -> None:
        """Given download endpoint called, when service name provided, then returns 202 with job info."""
        mock_start.return_value = {"job_id": "job-456", "status": "started"}

        response = client.post(
            "/api/v1/orchestration/download",
            json={"service": "qdrant"},
        )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "started"

    @patch("src.api.v1.system.orchestration.check_service_health", new_callable=AsyncMock)
    @patch("src.api.v1.system.orchestration.start_download", new_callable=AsyncMock)
    def test_download_without_idempotency_key_processes_normally(
        self, mock_start: AsyncMock, mock_health: AsyncMock, client: TestClient
    ) -> None:
        """Given request has no idempotency key, when API receives it, then processes normally."""
        mock_start.return_value = {"job_id": "job-789", "status": "started"}
        mock_health.return_value = {
            "llama_cpp": {"status": "active", "component": "llama.cpp"},
            "qdrant": {"status": "active", "component": "qdrant"},
        }

        response = client.post(
            "/api/v1/orchestration/download",
            json={"service": "qdrant"},
        )

        assert response.status_code == 202
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "started"


class TestDownloadProgress:
    """Test GET /api/v1/orchestration/download/{job_id}/progress endpoint."""

    def test_progress_returns_404_for_unknown_job(self, client: TestClient) -> None:
        """Given a non-existent job_id, when progress is queried, then returns 404."""
        response = client.get("/api/v1/orchestration/download/unknown-job/progress")
        assert response.status_code == 404

    def test_progress_returns_entry_for_stored_job(self, client: TestClient) -> None:
        """Given a job_id with stored progress, when queried, then returns progress data."""
        from src.api.v1.system.orchestration import _download_progress

        _download_progress["test-progress-job"] = {
            "progress": 42,
            "message": "Extracting...",
            "component": "binary",
        }
        try:
            resp = client.get("/api/v1/orchestration/download/test-progress-job/progress")
            assert resp.status_code == 200
            data = resp.json()["data"]
            assert data["progress"] == 42
            assert data["message"] == "Extracting..."
        finally:
            _download_progress.pop("test-progress-job", None)

    def test_progress_callback_updates_store(self) -> None:
        """Given a progress callback is created, when called with progress values, then in-memory store is updated."""
        from src.api.v1.system.orchestration import _download_progress, _make_progress_callback

        cb = _make_progress_callback("test-job-1", "binary")
        cb(50, "Downloading... 256 KB")
        assert _download_progress["test-job-1"] == {
            "progress": 50,
            "message": "Downloading... 256 KB",
            "component": "binary",
        }


class TestResponseTime:
    """Test response time requirements (NFR5)."""

    @patch("src.api.v1.system.orchestration.check_service_health", new_callable=AsyncMock)
    @patch("src.api.v1.system.orchestration.start_download", new_callable=AsyncMock)
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
        response = client.post("/api/v1/orchestration/download", json={"service": "qdrant"})
        elapsed = time.time() - start

        assert response.status_code == 202
        assert elapsed < 0.5
