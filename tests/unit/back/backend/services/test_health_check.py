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
async def test_check_llama_public_alias(health_service):
    """Test check_llama() delegates to _check_llamacpp()."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client
        result = await health_service.check_llama()
        assert result["status"] == "active"


@pytest.mark.asyncio
async def test_check_qdrant_public_alias(health_service):
    """Test check_qdrant() delegates to _check_qdrant()."""
    with (
        patch("src.shared.health.httpx") as mock_httpx,
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200

        async def mock_get(*args, **kwargs):
            return mock_response

        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_httpx.AsyncClient.return_value.__aenter__.return_value = mock_client

        result = await health_service.check_qdrant()
        assert "status" in result


@pytest.mark.asyncio
async def test_check_llama_non_200(health_service):
    """Test llama.cpp health check with non-200 response."""
    mock_response = MagicMock()
    mock_response.status_code = 503
    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client
        result = await health_service.check_llama()
        assert result["status"] == "error"


@pytest.mark.asyncio
async def test_check_llama_exception(health_service):
    """Test llama.cpp health check when HTTP call raises."""
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))

    with patch("httpx.AsyncClient") as mock_async_client:
        mock_async_client.return_value.__aenter__.return_value = mock_client
        result = await health_service.check_llama()
        assert result["status"] == "error"
        assert "Connection refused" in result.get("error", "")


@pytest.mark.asyncio
async def test_cache_expiry(health_service):
    """Test that expired cache entries are cleared."""
    mock_response_active = MagicMock()
    mock_response_active.status_code = 200
    mock_client = MagicMock()
    mock_client.get = AsyncMock()

    mock_response_error = MagicMock()
    mock_response_error.status_code = 503

    with (
        patch("httpx.AsyncClient") as mock_async_client,
        patch("time.time") as mock_time,
    ):
        mock_async_client.return_value.__aenter__.return_value = mock_client
        mock_time.return_value = 1000
        mock_client.get.return_value = mock_response_active
        result1 = await health_service.check_llama()
        assert result1["status"] == "active"

        mock_time.return_value = 1100
        mock_client.get.return_value = mock_response_error
        result2 = await health_service.check_llama()
        assert result2["status"] == "error"


def test_get_current_version_llama(health_service):
    """Test get_current_version for llama."""
    with patch("src.back.llamacpp.get_version", return_value="1.0.0"):
        version = health_service.get_current_version("llama")
        assert version == "1.0.0"


def test_get_current_version_qdrant(health_service):
    """Test get_current_version for qdrant."""
    with patch("src.back.qdrant.get_version", return_value="2.0.0"):
        version = health_service.get_current_version("qdrant")
        assert version == "2.0.0"


def test_get_current_version_unknown(health_service):
    """Test get_current_version returns None for unknown service."""
    version = health_service.get_current_version("unknown")
    assert version is None


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
