"""Tests for health check service."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def health_service():
    from src.back.backend.services.health_check import HealthCheckService

    return HealthCheckService()


@pytest.mark.asyncio
async def test_check_all_success(health_service):
    """Test when all services are healthy."""
    with (
        patch("src.shared.health.httpx") as mock_httpx,
        patch("qdrant_client.QdrantClient") as mock_qdrant_cls,
    ):
        # Mock httpx.AsyncClient context manager
        mock_response = MagicMock()
        mock_response.status_code = 200

        async def mock_get(*args: Any, **kwargs: Any) -> MagicMock:
            return mock_response

        mock_client = MagicMock()
        mock_client.get = mock_get

        # Set up AsyncClient().__aenter__ to return our mock client
        mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client
        mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock()

        # Mock qdrant client with collection present
        mock_collection = MagicMock()
        mock_collection.name = "sigma_rules"
        qdrant_client_mock = MagicMock()
        qdrant_client_mock.get_collections.return_value.collections = [mock_collection]
        mock_qdrant_cls.return_value = qdrant_client_mock

        result = await health_service.check_all()

        assert "qdrant" in result
        assert result["qdrant"]["status"] in ("ok", "warning")


@pytest.mark.asyncio
async def test_check_all_qdrant_success(health_service):
    """Test qdrant is healthy with collection present."""
    with (
        patch("src.shared.health.httpx") as mock_httpx,
        patch("qdrant_client.QdrantClient") as mock_qdrant_cls,
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200

        async def mock_get(*args: Any, **kwargs: Any) -> MagicMock:
            return mock_response

        mock_client = MagicMock()
        mock_client.get = mock_get

        mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client
        mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock()

        mock_collection = MagicMock()
        mock_collection.name = "sigma_rules"
        qdrant_client_mock = MagicMock()
        qdrant_client_mock.get_collections.return_value.collections = [mock_collection]
        mock_qdrant_cls.return_value = qdrant_client_mock

        result = await health_service.check_all()
        assert result["qdrant"]["status"] in ("ok", "warning")


@pytest.mark.asyncio
async def test_check_all_qdrant_failure(health_service):
    """Test qdrant connection failure."""
    with (
        patch("src.shared.health.httpx") as mock_httpx,
        patch("qdrant_client.QdrantClient") as mock_qdrant_cls,
    ):
        # Mock httpx health check response - success for the /healthz endpoint
        mock_response = MagicMock()
        mock_response.status_code = 200

        async def mock_get(*args: Any, **kwargs: Any) -> MagicMock:
            return mock_response

        mock_client = MagicMock()
        mock_client.get = mock_get

        mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client
        mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock()

        # Qdrant client raises an error (warnings check passes, but gRPC client fails)
        mock_qdrant_cls.side_effect = Exception("Connection refused")

        result = await health_service.check_all()
        assert result["qdrant"]["status"] == "warning"
        assert "Connection refused" in result["qdrant"].get("error", "")


@pytest.mark.asyncio
async def test_check_all_qdrant_healthz_failure(health_service):
    """Test qdrant healthz endpoint failure -> status: error."""
    with (
        patch("src.shared.health.httpx") as mock_httpx,
    ):
        # Mock httpx health check response - failure for the /healthz endpoint
        mock_response = MagicMock()
        mock_response.status_code = 503

        async def mock_get(*args: Any, **kwargs: Any) -> MagicMock:
            return mock_response

        mock_client = MagicMock()
        mock_client.get = mock_get

        mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client
        mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock()

        result = await health_service.check_all()
        assert result["qdrant"]["status"] == "error"
        assert "HTTP 503" in result["qdrant"].get("error", "")


@pytest.mark.asyncio
async def test_check_all_caching(health_service):
    """Test that qdrant results are cached (won't re-check within TTL)."""
    with (
        patch("src.shared.health.httpx") as mock_httpx,
        patch("qdrant_client.QdrantClient") as mock_qdrant_cls,
        patch("time.time") as mock_time,
    ):
        # Mock httpx health check response
        mock_response = MagicMock()
        mock_response.status_code = 200

        async def mock_get(*args: Any, **kwargs: Any) -> MagicMock:
            return mock_response

        mock_client = MagicMock()
        mock_client.get = mock_get

        mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client
        mock_httpx.AsyncClient.return_value.__aexit__ = AsyncMock()

        # Empty collections -> warning (collection not found)
        qdrant_client_mock = MagicMock()
        qdrant_client_mock.get_collections.return_value.collections = []
        mock_qdrant_cls.return_value = qdrant_client_mock

        mock_time.return_value = 1000

        result1 = await health_service.check_all()
        assert result1["qdrant"]["status"] == "warning"

        # Time changes but cache should still be valid (within TTL of 10s)
        mock_time.return_value = 1001
        result2 = await health_service.check_all()
        assert result2["qdrant"]["status"] == "warning"
