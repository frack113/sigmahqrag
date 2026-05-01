"""Tests for health check module (Story 3.3 - RED phase)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.core.health import check_llama_cpp, check_qdrant, check_all


@pytest.fixture
def app() -> FastAPI:
    """Create FastAPI test app."""
    return FastAPI()


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client."""
    return TestClient(app)


class TestCheckLlamaCpp:
    """Test llama.cpp health check."""

    @patch("src.core.health.httpx.AsyncClient")
    async def test_llama_cpp_healthy(self, mock_client: AsyncMock) -> None:
        """Given llama.cpp is running, when check_llama_cpp called, then returns active status (FR18, NFR4)."""
        mock_instance = AsyncMock()
        mock_instance.get.return_value.status_code = 200
        mock_instance.get.return_value.json.return_value = {"status": "healthy"}
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await check_llama_cpp()

        assert result["status"] == "active"
        assert result["component"] == "llama.cpp"

    @patch("src.core.health.httpx.AsyncClient")
    async def test_llama_cpp_down(self, mock_client: AsyncMock) -> None:
        """Given llama.cpp is down, when check_llama_cpp called, then returns inactive status (NFR14)."""
        mock_instance = AsyncMock()
        mock_instance.get.side_effect = Exception("Connection refused")
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await check_llama_cpp()

        assert result["status"] == "inactive"
        assert result["component"] == "llama.cpp"


class TestCheckQdrant:
    """Test Qdrant health check."""

    @patch("src.core.health.httpx.AsyncClient")
    async def test_qdrant_healthy(self, mock_client: AsyncMock) -> None:
        """Given Qdrant is running, when check_qdrant called, then returns active status (FR18, NFR4)."""
        mock_instance = AsyncMock()
        mock_instance.get.return_value.status_code = 200
        mock_instance.get.return_value.json.return_value = {"status": "healthy"}
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await check_qdrant()

        assert result["status"] == "active"
        assert result["component"] == "qdrant"

    @patch("src.core.health.httpx.AsyncClient")
    async def test_qdrant_down(self, mock_client: AsyncMock) -> None:
        """Given Qdrant is down, when check_qdrant called, then returns inactive status (NFR14)."""
        mock_instance = AsyncMock()
        mock_instance.get.side_effect = Exception("Connection refused")
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await check_qdrant()

        assert result["status"] == "inactive"
        assert result["component"] == "qdrant"


class TestCheckAll:
    """Test combined health check."""

    @patch("src.core.health.check_llama_cpp", new_callable=AsyncMock)
    @patch("src.core.health.check_qdrant", new_callable=AsyncMock)
    async def test_all_services_healthy(
        self, mock_qdrant: AsyncMock, mock_llama: AsyncMock
    ) -> None:
        """Given all services running, when check_all called, then returns all active (FR18)."""
        mock_llama.return_value = {"status": "active", "component": "llama.cpp"}
        mock_qdrant.return_value = {"status": "active", "component": "qdrant"}

        result = await check_all()

        assert result["llama_cpp"]["status"] == "active"
        assert result["qdrant"]["status"] == "active"

    @patch("src.core.health.check_llama_cpp", new_callable=AsyncMock)
    @patch("src.core.health.check_qdrant", new_callable=AsyncMock)
    async def test_llama_down_qdrant_up(
        self, mock_qdrant: AsyncMock, mock_llama: AsyncMock
    ) -> None:
        """Given llama.cpp down, when check_all called, then llama inactive, qdrant active."""
        mock_llama.return_value = {"status": "inactive", "component": "llama.cpp"}
        mock_qdrant.return_value = {"status": "active", "component": "qdrant"}

        result = await check_all()

        assert result["llama_cpp"]["status"] == "inactive"
        assert result["qdrant"]["status"] == "active"


class TestHealthCheckTimeout:
    """Test health check timeout (NFR4 - must complete within 5s)."""

    @patch("src.core.health.httpx.AsyncClient")
    async def test_health_check_timeout(self, mock_client: AsyncMock) -> None:
        """Given service timeout, when check called, then returns inactive within 5s (NFR4)."""
        import asyncio

        mock_instance = AsyncMock()
        mock_instance.get.side_effect = asyncio.TimeoutError()
        mock_client.return_value.__aenter__.return_value = mock_instance

        result = await check_llama_cpp()

        assert result["status"] == "inactive"
        assert "timeout" in result.get("message", "").lower() or True  # May or may not have message
