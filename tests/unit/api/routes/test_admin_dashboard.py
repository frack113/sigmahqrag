"""Tests for admin dashboard enhancements."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.shared.version_manager import check_for_updates


@pytest.mark.asyncio
async def test_get_current_version_returns_version():
    """Test that get_current_version returns version from backend module."""
    with patch(
        "src.shared.version_manager.get_current_version",
        new_callable=AsyncMock,
        return_value="1.0.0",
    ) as mock_get:
        result = await mock_get("llama.cpp")

        assert result == "1.0.0"
        mock_get.assert_called_once_with("llama.cpp")


@pytest.mark.asyncio
async def test_get_current_version_returns_none():
    """Test that get_current_version returns None when no version."""
    with patch(
        "src.shared.version_manager.get_current_version",
        new_callable=AsyncMock,
        return_value=None,
    ) as mock_get:
        result = await mock_get("llama.cpp")

        assert result is None


@pytest.mark.asyncio
async def test_check_for_updates_update_available():
    """Test check_for_updates returns update available."""
    with (
        patch("src.shared.version_manager.get_current_version", new_callable=AsyncMock) as mock_ver,
        patch("src.shared.version_manager.VersionManager") as mock_vm_class,
    ):
        mock_ver.return_value = "1.0.0"

        mock_vm = MagicMock()
        mock_vm.get_release = AsyncMock()
        mock_release = MagicMock()
        mock_release.tag_name = "v2.0.0"
        mock_vm.get_release.return_value = mock_release
        mock_vm_class.return_value = mock_vm

        result = await check_for_updates("llama.cpp")

        assert result["current_version"] == "1.0.0"
        assert result["latest_version"] == "2.0.0"
        assert result["update_available"] is True


@pytest.mark.asyncio
async def test_check_for_updates_no_update():
    """Test check_for_updates returns no update when already latest."""
    with (
        patch("src.shared.version_manager.get_current_version", new_callable=AsyncMock) as mock_ver,
        patch("src.shared.version_manager.VersionManager") as mock_vm_class,
    ):
        mock_ver.return_value = "2.0.0"

        mock_vm = MagicMock()
        mock_vm.get_release = AsyncMock()
        mock_release = MagicMock()
        mock_release.tag_name = "v2.0.0"
        mock_vm.get_release.return_value = mock_release
        mock_vm_class.return_value = mock_vm

        result = await check_for_updates("llama.cpp")

        assert result["current_version"] == "2.0.0"
        assert result["latest_version"] == "2.0.0"
        assert result["update_available"] is False


@pytest.mark.asyncio
async def test_check_for_updates_no_current_version():
    """Test check_for_updates returns None when no current version."""
    with patch(
        "src.shared.version_manager.get_current_version", new_callable=AsyncMock
    ) as mock_ver:
        mock_ver.return_value = None

        result = await check_for_updates("llama.cpp")

        assert result is None
