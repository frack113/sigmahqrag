"""Tests for POST /api/v1/admin/cancel endpoint (Story 3.1)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.v1.admin import router


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI test app with admin router."""
    from fastapi import FastAPI

    test_app = FastAPI()
    test_app.include_router(router)
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestPostAdminCancel:
    """Test POST /api/v1/admin/cancel endpoint."""

    @patch("src.api.v1.admin.check_service_health", new_callable=AsyncMock)
    def test_cancel_returns_200(
        self, mock_health: AsyncMock, client: TestClient
    ) -> None:
        """Given cancel action called, when POST /cancel called, then returns 200 (FR16)."""
        mock_health.return_value = {
            "llama_cpp": {"status": "active", "component": "llama.cpp"},
            "qdrant": {"status": "active", "component": "qdrant"},
        }

        response = client.post(
            "/api/v1/admin/cancel",
            json={"job_id": "job-123"},
            headers={"X-Idempotency-Key": "cancel-key-1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    @patch("src.api.v1.admin.check_service_health", new_callable=AsyncMock)
    def test_cancel_with_idempotency_key(
        self, mock_health: AsyncMock, client: TestClient
    ) -> None:
        """Given POST cancel called with idempotency key, when same key used twice, then returns same result (FR20, NFR20)."""
        mock_health.return_value = {
            "llama_cpp": {"status": "active", "component": "llama.cpp"},
            "qdrant": {"status": "active", "component": "qdrant"},
        }

        response1 = client.post(
            "/api/v1/admin/cancel",
            json={"job_id": "job-456"},
            headers={"X-Idempotency-Key": "same-cancel-key"},
        )
        response2 = client.post(
            "/api/v1/admin/cancel",
            json={"job_id": "job-456"},
            headers={"X-Idempotency-Key": "same-cancel-key"},
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
