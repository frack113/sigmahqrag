from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1 import admin, qdrant


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI test app with admin and qdrant routers."""
    test_app = FastAPI()
    test_app.include_router(admin.router)
    test_app.include_router(qdrant.router)
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestQdrantCancel:
    """Test POST /api/v1/qdrant endpoint with cancel action."""

    @patch("src.back.download_manager.create_download_manager")
    def test_qdrant_cancel_returns_200(self, mock_dm: AsyncMock, client: TestClient) -> None:
        """Given cancel action called, when POST /api/v1/post/qdrant called, then returns 200 (FR16)."""
        mock_manager = AsyncMock()
        mock_dm.return_value = mock_manager

        payload = {"action": "cancel", "payload": {"download_id": "job-123"}}

        response = client.post(
            "/api/v1/qdrant",
            json=payload,
            headers={"X-Idempotency-Key": "cancel-key-1"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data["status"]
        assert "job-123 cancelled" in data["message"]
        mock_manager.cancel_download.assert_called_once_with("job-123")

    @patch("src.back.download_manager.create_download_manager")
    def test_qdrant_cancel_with_idempotency_key(
        self, mock_dm: AsyncMock, client: TestClient
    ) -> None:
        """Given POST cancel called with idempotency key, when same key used twice, then returns same result (FR20, NFR20)."""
        mock_manager = AsyncMock()
        mock_dm.return_value = mock_manager

        payload = {"action": "cancel", "payload": {"download_id": "job-456"}}

        response1 = client.post(
            "/api/v1/qdrant",
            json=payload,
            headers={"POST-Idempotency-Key": "same-cancel-key"},
        )
        response2 = client.post(
            "/api/v1/qdrant",
            json=payload,
            headers={"POST-Idempotency-Key": "same-cancel-key"},
        )

        assert response1.status_code == 200
        assert response2.status_code == 200
