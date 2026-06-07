"""Tests for update service."""

from unittest.mock import AsyncMock

import pytest

from src.application.update_manager import UpdateService, create_update_service


class FakeHealthChecker:
    def __init__(self) -> None:
        self.check_llama = AsyncMock(return_value={"status": "active"})
        self.check_qdrant = AsyncMock(return_value={"status": "active"})

    def get_current_version(self, service: str) -> str | None:
        versions = {"llama.cpp": "b1234", "qdrant": "v1.0.0"}
        return versions.get(service)


class TestUpdateService:
    @pytest.fixture
    def health_checker(self) -> FakeHealthChecker:
        return FakeHealthChecker()

    @pytest.fixture
    def service(self, health_checker: FakeHealthChecker) -> UpdateService:
        return UpdateService(health_checker=health_checker)

    @pytest.mark.asyncio
    async def test_check_service_health_llama(self, service: UpdateService) -> None:
        result = await service._check_service_health("llama.cpp")
        assert result is True

    @pytest.mark.asyncio
    async def test_check_service_health_qdrant(self, service: UpdateService) -> None:
        result = await service._check_service_health("qdrant")
        assert result is True

    @pytest.mark.asyncio
    async def test_check_service_health_unknown(self, service: UpdateService) -> None:
        result = await service._check_service_health("unknown")
        assert result is False

    @pytest.mark.asyncio
    async def test_check_service_health_inactive(self, health_checker: FakeHealthChecker) -> None:
        health_checker.check_llama = AsyncMock(return_value={"status": "inactive"})
        svc = UpdateService(health_checker=health_checker)
        result = await svc._check_service_health("llama.cpp")
        assert result is False

    @pytest.mark.asyncio
    async def test_check_service_health_exception(self, health_checker: FakeHealthChecker) -> None:
        health_checker.check_llama = AsyncMock(side_effect=RuntimeError("fail"))
        svc = UpdateService(health_checker=health_checker)
        result = await svc._check_service_health("llama.cpp")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_status(self, service: UpdateService) -> None:
        result = await service.get_status()
        assert "services" in result
        assert "llama_cpp" in result["services"]
        assert "qdrant" in result["services"]

        llama_info = result["services"]["llama_cpp"]
        assert llama_info["current_version"] == "b1234"

        qdrant_info = result["services"]["qdrant"]
        assert qdrant_info["current_version"] == "v1.0.0"


class TestCreateUpdateService:
    def test_creates_instance(self) -> None:
        svc = create_update_service()
        assert isinstance(svc, UpdateService)

    def test_singleton(self) -> None:
        svc1 = create_update_service()
        svc2 = create_update_service()
        assert svc1 is svc2
