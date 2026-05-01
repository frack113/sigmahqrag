"""Tests for admin dashboard enhancements."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.admin.version_manager import check_for_updates, get_current_version


@pytest.mark.asyncio
async def test_get_current_version_returns_version():
    """Test that get_current_version returns version from backup manager."""
    with patch("src.admin.backup_manager.create_backup_manager") as mock_create:
        mock_mgr = MagicMock()
        mock_mgr.get_current_version.return_value = "1.0.0"
        mock_create.return_value = mock_mgr

        result = await get_current_version("llama.cpp")

        assert result == "1.0.0"
        mock_mgr.get_current_version.assert_called_once_with("llama.cpp")


@pytest.mark.asyncio
async def test_get_current_version_returns_none():
    """Test that get_current_version returns None when no version."""
    with patch("src.admin.backup_manager.create_backup_manager") as mock_create:
        mock_mgr = MagicMock()
        mock_mgr.get_current_version.return_value = None
        mock_create.return_value = mock_mgr

        result = await get_current_version("llama.cpp")

        assert result is None


@pytest.mark.asyncio
async def test_check_for_updates_update_available():
    """Test check_for_updates returns update available."""
    with patch("src.admin.version_manager.get_current_version", new_callable=AsyncMock) as mock_ver, \
         patch("src.admin.version_manager.VersionManager") as mock_vm_class:

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
    with patch("src.admin.version_manager.get_current_version", new_callable=AsyncMock) as mock_ver, \
         patch("src.admin.version_manager.VersionManager") as mock_vm_class:

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
    with patch("src.admin.version_manager.get_current_version", new_callable=AsyncMock) as mock_ver:
        mock_ver.return_value = None

        result = await check_for_updates("llama.cpp")

        assert result is None
