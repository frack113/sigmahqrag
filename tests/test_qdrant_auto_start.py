"""Tests for Qdrant auto-start on application launch."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

import src.back.qdrant.auto_start as _auto_start_mod
from src.back.qdrant.auto_start import start_qdrant, stop_qdrant


@pytest.fixture(autouse=True)
def reset_global_state():
    _auto_start_mod._qdrant_started_by_us = False
    _auto_start_mod._started_binary_service = None
    yield
    _auto_start_mod._qdrant_started_by_us = False
    _auto_start_mod._started_binary_service = None


@pytest.fixture
def mock_health():
    return AsyncMock()


@pytest.fixture
def mock_installer():
    inst = AsyncMock()
    inst.download_binary = AsyncMock(return_value={"success": True})
    return inst


@pytest.fixture
def mock_binary_service():
    svc = AsyncMock()
    svc.start = AsyncMock(return_value={"success": True})
    svc.stop = AsyncMock(return_value={"success": True})
    return svc


@pytest.fixture(autouse=True)
def mock_path_not_exists():
    with (
        patch.object(Path, "exists", return_value=False),
        patch.object(Path, "is_dir", return_value=False),
    ):
        yield


class FakeConfig:
    """Simulated config matching the fields used by auto_start."""

    qdrant_mode: str = "managed"
    qdrant_port: int = 6333
    qdrant_binary_path: str = "data/bin/qdrant"


@pytest.fixture(autouse=True)
def mock_config():
    fake = FakeConfig()
    with patch("src.shared.get_config", return_value=fake):
        yield fake


class TestStartQdrant:
    async def test_skips_when_already_running(self, mock_health, mock_config):
        mock_health.return_value = {"status": "active"}
        await start_qdrant(health_check=mock_health)
        mock_health.assert_awaited_once()
        assert not _auto_start_mod._qdrant_started_by_us

    async def test_skips_when_mode_external(self, mock_config):
        mock_config.qdrant_mode = "external"
        await start_qdrant()
        assert not _auto_start_mod._qdrant_started_by_us

    async def test_handles_health_exception_gracefully(
        self, mock_health, mock_installer, mock_binary_service, mock_config
    ):
        mock_health.side_effect = RuntimeError("connection failed")
        with patch.object(Path, "exists", return_value=True):
            await start_qdrant(
                health_check=mock_health,
                installer_service=mock_installer,
                binary_service=mock_binary_service,
            )
        assert mock_binary_service.start.awaited

    async def test_downloads_and_starts_qdrant(
        self, mock_health, mock_installer, mock_binary_service, mock_config
    ):
        mock_health.side_effect = [
            {"status": "inactive"},
            {"status": "active"},
        ]
        await start_qdrant(
            health_check=mock_health,
            installer_service=mock_installer,
            binary_service=mock_binary_service,
        )
        mock_installer.download_binary.assert_awaited_once()
        mock_binary_service.start.assert_awaited_once()
        assert _auto_start_mod._qdrant_started_by_us

    async def test_starts_without_download_when_binary_exists(
        self, mock_health, mock_binary_service, mock_config
    ):
        mock_health.side_effect = [
            {"status": "inactive"},
            {"status": "active"},
        ]
        with patch.object(Path, "exists", return_value=True):
            await start_qdrant(
                health_check=mock_health,
                binary_service=mock_binary_service,
            )
        mock_binary_service.start.assert_awaited_once()
        assert _auto_start_mod._qdrant_started_by_us

    async def test_logs_warning_on_download_failure(
        self, mock_health, mock_installer, mock_config, caplog
    ):
        mock_installer.download_binary = AsyncMock(
            return_value={"success": False, "error": "Network error"}
        )
        mock_health.return_value = {"status": "inactive"}
        await start_qdrant(
            health_check=mock_health,
            installer_service=mock_installer,
        )
        assert "Failed to download" in caplog.text
        assert not _auto_start_mod._qdrant_started_by_us

    async def test_logs_warning_on_start_failure(
        self, mock_health, mock_installer, mock_binary_service, mock_config, caplog
    ):
        mock_binary_service.start = AsyncMock(
            return_value={"success": False, "error": "Port in use"}
        )
        mock_health.return_value = {"status": "inactive"}
        await start_qdrant(
            health_check=mock_health,
            installer_service=mock_installer,
            binary_service=mock_binary_service,
        )
        assert "Failed to start" in caplog.text
        assert not _auto_start_mod._qdrant_started_by_us

    async def test_sets_flag_on_health_timeout(
        self, mock_health, mock_installer, mock_binary_service, mock_config
    ):
        mock_health.return_value = {"status": "inactive"}
        await start_qdrant(
            health_check=mock_health,
            installer_service=mock_installer,
            binary_service=mock_binary_service,
        )
        assert _auto_start_mod._qdrant_started_by_us
        assert _auto_start_mod._started_binary_service is mock_binary_service


class TestStopQdrant:
    async def test_skips_if_not_started_by_us(self):
        await stop_qdrant()

    async def test_stops_using_stored_service_instance(self):
        _auto_start_mod._qdrant_started_by_us = True
        mock_svc = AsyncMock()
        mock_svc.stop = AsyncMock(return_value={"success": True})
        _auto_start_mod._started_binary_service = mock_svc
        await stop_qdrant()
        mock_svc.stop.assert_awaited_once()

    async def test_creates_service_if_no_stored_instance(self):
        _auto_start_mod._qdrant_started_by_us = True
        with patch("src.back.qdrant.service.QdrantBinaryService") as mock_svc_cls:
            mock_svc = AsyncMock()
            mock_svc.stop = AsyncMock(return_value={"success": True})
            mock_svc_cls.return_value = mock_svc
            await stop_qdrant()
            mock_svc.stop.assert_awaited_once()

    async def test_resets_flag_on_stop(self):
        _auto_start_mod._qdrant_started_by_us = True
        mock_svc = AsyncMock()
        mock_svc.stop = AsyncMock(return_value={"success": True})
        _auto_start_mod._started_binary_service = mock_svc
        await stop_qdrant()
        assert not _auto_start_mod._qdrant_started_by_us

    async def test_handles_stop_exception_gracefully(self):
        _auto_start_mod._qdrant_started_by_us = True
        mock_svc = AsyncMock()
        mock_svc.stop.side_effect = RuntimeError("stop failed")
        _auto_start_mod._started_binary_service = mock_svc
        await stop_qdrant()
        assert not _auto_start_mod._qdrant_started_by_us
