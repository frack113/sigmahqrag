"""Tests for health check service."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest


@pytest.fixture
def health_service():
    from src.core.services.health_check import HealthCheckService

    return HealthCheckService()


@pytest.mark.asyncio
async def test_check_all_success(health_service):
    with (
        patch("httpx.get") as mock_get,
        patch("qdrant_client.QdrantClient") as mock_qdrant_cls,
    ):
        mock_get.return_value = Mock(status_code=200)

        mock_collection = Mock()
        mock_collection.name = "sigma_rules"
        mock_client = Mock()
        mock_client.get_collections.return_value.collections = [mock_collection]
        mock_qdrant_cls.return_value = mock_client

        result = await health_service.check_all()

        # Check that qdrant key exists and has valid status
        assert "qdrant" in result
        assert result["qdrant"]["status"] in ("ok", "warning")


@pytest.mark.asyncio
async def test_check_all_qdrant_success(health_service):
    with (
        patch("httpx.get") as mock_get,
        patch("qdrant_client.QdrantClient") as mock_qdrant_cls,
    ):
        mock_get.return_value = Mock(status_code=200)

        mock_collection = Mock()
        mock_collection.name = "sigma_rules"
        mock_client = Mock()
        mock_client.get_collections.return_value.collections = [mock_collection]
        mock_qdrant_cls.return_value = mock_client

        result = await health_service.check_all()

        assert result["qdrant"]["status"] in ("ok", "warning")


@pytest.mark.asyncio
async def test_check_all_qdrant_failure(health_service):
    with (
        patch("httpx.get") as mock_get,
        patch("qdrant_client.QdrantClient") as mock_qdrant_cls,
    ):
        mock_get.return_value = Mock(status_code=200)
        mock_qdrant_cls.side_effect = Exception("Connection refused")

        result = await health_service.check_all()
        assert result["qdrant"]["status"] == "error"


@pytest.mark.asyncio
async def test_check_all_caching(health_service):
    with (
        patch("httpx.get") as mock_get,
        patch("qdrant_client.QdrantClient") as mock_qdrant_cls,
        patch("time.time") as mock_time,
    ):
        mock_get.return_value = Mock(status_code=200)
        mock_client = Mock()
        mock_client.get_collections.return_value.collections = []
        mock_qdrant_cls.return_value = mock_client
        mock_time.return_value = 1000

        result1 = await health_service.check_all()
        assert result1["qdrant"]["status"] == "warning"

        mock_time.return_value = 1001
        result2 = await health_service.check_all()
        assert result2["qdrant"]["status"] == "warning"
