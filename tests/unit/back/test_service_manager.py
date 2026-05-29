"""Tests for global service manager."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import src.back.service_manager
from src.back.service_manager import get_subprocess_manager, shutdown_all_services


class TestGetSubprocessManager:
    def test_creates_and_caches(self) -> None:
        mock_config = MagicMock()
        mock_config.paths_logs_dir = "data/logs"
        with (
            patch.object(src.back.service_manager, "_subprocess_manager", None),
            patch("src.shared.get_config", return_value=mock_config),
            patch("src.shared.subprocess_manager.SubprocessManager") as MockSPM,
        ):
            mgr1 = get_subprocess_manager()
            mgr2 = get_subprocess_manager()
            MockSPM.assert_called_once()
            assert mgr1 is mgr2


class TestShutdownAllServices:
    @pytest.mark.asyncio
    async def test_shuts_down(self) -> None:
        mock_mgr = AsyncMock()
        mock_mgr.stop_all = AsyncMock(return_value={})
        with patch("src.back.service_manager.get_subprocess_manager", return_value=mock_mgr):
            await shutdown_all_services()
            mock_mgr.stop_all.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_handles_exception_gracefully(self) -> None:
        mock_mgr = AsyncMock()
        mock_mgr.stop_all = AsyncMock(side_effect=RuntimeError("fail"))
        with patch("src.back.service_manager.get_subprocess_manager", return_value=mock_mgr):
            await shutdown_all_services()
            mock_mgr.stop_all.assert_awaited_once()
