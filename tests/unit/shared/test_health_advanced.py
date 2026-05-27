"""Advanced tests for health check service."""

from unittest.mock import patch

import httpx
import pytest

from src.shared.health import check_service_health


class TestCheckServiceHealth:
    @pytest.mark.asyncio
    async def test_success_200(self) -> None:
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value.status_code = 200
            result = await check_service_health("qdrant", "localhost", 6333)
            assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_inactive_non_200(self) -> None:
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.return_value.status_code = 503
            result = await check_service_health("qdrant", "localhost", 6333)
            assert result["status"] == "inactive"
            assert "503" in result["message"]

    @pytest.mark.asyncio
    async def test_timeout(self) -> None:
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = (
                httpx.TimeoutException("timeout")
            )
            result = await check_service_health("qdrant", "localhost", 6333)
            assert result["status"] == "inactive"
            assert result["message"] == "timeout"

    @pytest.mark.asyncio
    async def test_connection_refused(self) -> None:
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.ConnectError(
                "connection refused"
            )
            result = await check_service_health("qdrant", "localhost", 6333)
            assert result["status"] == "inactive"
            assert "refused" in result["message"]

    @pytest.mark.asyncio
    async def test_generic_http_error(self) -> None:
        with patch("httpx.AsyncClient") as mock_client:
            mock_client.return_value.__aenter__.return_value.get.side_effect = httpx.HTTPError(
                "generic error"
            )
            result = await check_service_health("qdrant", "localhost", 6333)
            assert result["status"] == "inactive"
            assert "generic" in result["message"]
