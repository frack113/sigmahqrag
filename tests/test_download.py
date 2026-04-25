"""Tests for download manager functionality."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.admin.download_manager import DownloadManager, DownloadTask
from src.admin.temp_manager import TempManager
from src.admin.version_manager import ReleaseAsset, ReleaseInfo, VersionManager
from src.exceptions import DownloadError


@pytest.fixture
def temp_manager(tmp_path):
    """Create a temp manager with tmp_path."""
    return TempManager(temp_dir=tmp_path)


@pytest.fixture
def version_manager():
    """Create a mock version manager."""
    return MagicMock(spec=VersionManager)


@pytest.fixture
def download_manager(version_manager, temp_manager):
    """Create a download manager."""
    return DownloadManager(
        version_manager=version_manager,
        temp_manager_manager=temp_manager,
    )


class TestTempManager:
    """Tests for TempManager."""

    def test_create_temp_file(self, temp_manager, tmp_path):
        """Test creating a temp file."""
        result = temp_manager.create_temp_file("test-id-123")

        assert result.parent == tmp_path
        assert result.name == "test-id-123.tmp"

    def test_cleanup_existing_file(self, temp_manager, tmp_path):
        """Test cleaning up an existing temp file."""
        temp_file = tmp_path / "test.tmp"
        temp_file.write_text("test")

        result = temp_manager.cleanup(temp_file)

        assert result is True
        assert not temp_file.exists()

    def test_cleanup_nonexistent_file(self, temp_manager, tmp_path):
        """Test cleaning up a non-existent temp file."""
        temp_file = tmp_path / "nonexistent.tmp"

        result = temp_manager.cleanup(temp_file)

        assert result is False


class TestVersionManager:
    """Tests for VersionManager."""

    @pytest.mark.asyncio
    async def test_detect_platform(self):
        """Test platform detection."""
        manager = VersionManager()
        os_name, arch = manager._detect_platform()

        assert os_name in ("windows", "linux", "macos")
        assert arch in ("x64", "arm64")

    def test_find_matching_asset_with_patterns(self):
        """Test finding matching asset by pattern."""
        manager = VersionManager()

        import platform
        system = platform.system().lower()

        if system == "windows":
            asset_name = "llama-windows-x64"
        elif system == "darwin":
            asset_name = "llama-macos-x64"
        else:
            asset_name = "llama-linux-x64"

        release = ReleaseInfo(
            tag_name="v1.0.0",
            assets=[
                ReleaseAsset(
                    name=asset_name,
                    browser_download_url="https://example.com/llama-linux-x64",
                    size=1000000,
                ),
            ],
        )

        asset = manager.find_matching_asset(release, "llama.cpp")

        assert asset is not None
        assert asset.name == asset_name

    def test_get_binary_name_llama(self):
        """Test getting binary name for llama.cpp."""
        manager = VersionManager()

        asset = ReleaseAsset(
            name="llama-linux-x64",
            browser_download_url="https://example.com",
            size=1000000,
        )

        result = manager.get_binary_name("llama.cpp", asset)

        assert result.name == "llama-server"

    def test_get_binary_name_qdrant(self):
        """Test getting binary name for qdrant."""
        manager = VersionManager()

        asset = ReleaseAsset(
            name="qdrant",
            browser_download_url="https://example.com",
            size=1000000,
        )

        result = manager.get_binary_name("qdrant", asset)

        assert result.name == "qdrant"


class TestDownloadManager:
    """Tests for DownloadManager."""

    @pytest.mark.asyncio
    async def test_start_download_unsupported_service(self, download_manager):
        """Test downloading unsupported service raises error."""
        with pytest.raises(DownloadError) as exc_info:
            await download_manager.start_download("unknown", "latest")

        assert "Unsupported service" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_download_no_matching_asset(self, download_manager, version_manager):
        """Test download with no matching asset raises error."""
        version_manager.get_release = AsyncMock(return_value=ReleaseInfo(
            tag_name="v1.0.0",
            assets=[],
        ))
        download_manager.version_manager.find_matching_asset = MagicMock(return_value=None)

        with pytest.raises(DownloadError) as exc_info:
            await download_manager.start_download("llama.cpp", "latest")

        assert "No matching binary found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_download_success(self, download_manager, version_manager):
        """Test successful download initiation."""
        version_manager.get_release = AsyncMock(return_value=ReleaseInfo(
            tag_name="v1.0.0",
            assets=[
                ReleaseAsset(
                    name="llama-linux-x64",
                    browser_download_url="https://example.com/llama",
                    size=1000000,
                ),
            ],
        ))
        version_manager.find_matching_asset = MagicMock(
            return_value=ReleaseAsset(
                name="llama-linux-x64",
                browser_download_url="https://example.com/llama",
                size=1000000,
            )
        )

        result = await download_manager.start_download("llama.cpp", "latest")

        assert result["status"] == "started"
        assert result["service"] == "llama.cpp"
        assert "download_id" in result

    @pytest.mark.asyncio
    async def test_cancel_download_not_found(self, download_manager):
        """Test cancelling non-existent download."""
        result = await download_manager.cancel_download("non-existent-id")

        assert result["status"] == "not_found"

    @pytest.mark.asyncio
    async def test_get_progress_not_found(self, download_manager):
        """Test getting progress for non-existent download."""
        result = download_manager.get_progress("non-existent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_progress_stream_not_found(self, download_manager):
        """Test getting progress stream for non-existent download."""
        result = download_manager.get_progress_stream("non-existent-id")

        assert result is None


class TestDownloadCancel:
    """Tests for download cancellation."""

    @pytest.mark.asyncio
    async def test_cancel_active_download(self, download_manager, version_manager, temp_manager, tmp_path):
        """Test cancelling an active download."""
        version_manager.get_release = AsyncMock(return_value=ReleaseInfo(
            tag_name="v1.0.0",
            assets=[
                ReleaseAsset(
                    name="llama-linux-x64",
                    browser_download_url="https://example.com/llama",
                    size=1000000,
                ),
            ],
        ))
        version_manager.find_matching_asset = MagicMock(
            return_value=ReleaseAsset(
                name="llama-linux-x64",
                browser_download_url="https://example.com/llama",
                size=1000000,
            )
        )

        result = await download_manager.start_download("llama.cpp", "latest")
        download_id = result["download_id"]

        await asyncio.sleep(0.1)

        cancel_result = await download_manager.cancel_download(download_id)

        assert cancel_result["status"] == "cancelled"