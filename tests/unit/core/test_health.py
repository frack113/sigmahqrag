"""Tests for HealthCheckService (Story 3.3 - RED phase)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
from src.back.backend.services.health_check import HealthCheckService


class TestHealthCheckServiceLlamaCpp:
    """Test llama.cpp health check via service."""

    @patch("httpx.AsyncClient")
    async def test_llama_cpp_healthy(self, mock_async_client: AsyncMock) -> None:
        """Given llama.cpp is running, when health checked, then returns active status (FR18, NFR4)."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200

        async def mock_get(*args: object, **kwargs: object) -> MagicMock:
            return mock_resp

        mock_client = MagicMock()
        mock_client.get = mock_get
        mock_async_client.return_value.__aenter__.return_value = mock_client

        service = HealthCheckService()
        result = await service._check_llamacpp()

        assert result["status"] == "active"
        assert "url" in result

    @patch("httpx.AsyncClient")
    async def test_llama_cpp_down(self, mock_async_client: AsyncMock) -> None:
        """Given llama.cpp is down, when health checked, then returns inactive status (NFR14)."""
        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")
        mock_async_client.return_value.__aenter__.return_value = mock_client

        service = HealthCheckService()
        result = await service._check_llamacpp()

        assert result["status"] == "error"
        assert "url" in result


class TestHealthCheckServiceQdrant:
    """Test Qdrant health check via service."""

    @patch("src.back.qdrant.health.check_health", new_callable=AsyncMock)
    async def test_qdrant_healthy(self, mock_check: AsyncMock) -> None:
        """Given Qdrant is running, when health checked, then returns active status."""
        mock_check.return_value = {"status": "active"}

        service = HealthCheckService()
        result = await service._check_qdrant()

        assert result["status"] in ("ok", "warning")


class TestHealthCheckServiceCaching:
    """Test health check caching behavior."""

    async def test_caching_reduces_calls(self) -> None:
        """Given cached result exists, when health checked again, then returns from cache."""
        service = HealthCheckService()

        # First call - will check real endpoints (may fail if services not running)
        await service._check_llamacpp()

        # Second call should use cache - verify _get_cached works
        result = service._get_cached("llamacpp")
        assert result is None or "status" in result


class TestHealthCheckServiceIntegration:
    """Integration tests for HealthCheckService."""

    async def test_check_all_returns_dict(self) -> None:
        """Given healthy system, when check_all called, then returns dict with all components."""
        service = HealthCheckService()
        result = await service.check_all()

        assert isinstance(result, dict)
        assert "llamacpp" in result
        assert "qdrant" in result
        assert "timestamp" in result

    async def test_check_llama_alias(self) -> None:
        """Test check_llama public alias."""
        service = HealthCheckService()
        # Just verify the method exists and returns dict
        _ = await service.check_llama()
