"""Tests for llama.cpp service."""

import platform
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestPlatformDetection:
    """Test platform detection functions."""

    @patch("sigmahqrag.services.llama.download.platform.system")
    @patch("sigmahqrag.services.llama.download.platform.machine")
    def test_windows_platform(self, mock_machine, mock_system):
        """Test Windows platform detection."""
        mock_system.return_value = "Windows"
        mock_machine.return_value = "amd64"

        from sigmahqrag.services.llama.download import get_platform_info

        info = get_platform_info()
        assert info["system"] == "windows"
        assert info["extension"] == ".exe"
        assert info["archive"] == ".zip"

    @patch("sigmahqrag.services.llama.download.platform.system")
    @patch("sigmahqrag.services.llama.download.platform.machine")
    def test_macos_arm64_platform(self, mock_machine, mock_system):
        """Test macOS ARM64 platform detection."""
        mock_system.return_value = "Darwin"
        mock_machine.return_value = "arm64"

        from sigmahqrag.services.llama.download import get_platform_info

        info = get_platform_info()
        assert info["system"] == "macos"
        assert info["arch"] == "arm64"

    @patch("sigmahqrag.services.llama.download.platform.system")
    @patch("sigmahqrag.services.llama.download.platform.machine")
    def test_linux_platform(self, mock_machine, mock_system):
        """Test Linux platform detection."""
        mock_system.return_value = "Linux"
        mock_machine.return_value = "x86_64"

        from sigmahqrag.services.llama.download import get_platform_info

        info = get_platform_info()
        assert info["system"] == "linux"
        assert info["archive"] == ".gz"


class TestDownloadUrl:
    """Test download URL generation."""

    def test_latest_url_windows(self):
        """Test URL generation for latest Windows version."""
        with patch("sigmahqrag.services.llama.download.get_platform_info") as mock_info:
            mock_info.return_value = {
                "system": "windows",
                "arch": "x86_64",
                "extension": ".exe",
                "archive": ".zip",
            }

            from sigmahqrag.services.llama.download import get_download_url

            url = get_download_url("latest")
            assert "llama-server-windows-x86_64.exe.zip" in url

    def test_specific_version_url(self):
        """Test URL generation for specific version."""
        with patch("sigmahqrag.services.llama.download.get_platform_info") as mock_info:
            mock_info.return_value = {
                "system": "linux",
                "arch": "x86_64",
                "extension": "",
                "archive": ".gz",
            }

            from sigmahqrag.services.llama.download import get_download_url

            url = get_download_url("v1.0.0")
            assert "download/v1.0.0" in url
            assert "llama-server-linux-x86_64" in url


class TestLlamaService:
    """Test LlamaService class."""

    def test_init_defaults(self):
        """Test default initialization."""
        with patch("sigmahqrag.services.llama.client.get_binary_path"):
            from sigmahqrag.services.llama import LlamaService

            service = LlamaService()
            assert service.port == 8080
            assert service.host == "127.0.0.1"
            assert service.binary_path.name in ("llama-server", "llama-server.exe")

    def test_init_custom_params(self):
        """Test custom initialization parameters."""
        from sigmahqrag.services.llama import LlamaService

        service = LlamaService(
            binary_path=Path("/custom/path/llama-server"),
            port=9090,
            host="localhost",
        )
        assert service.port == 9090
        assert service.host == "localhost"
        assert service.binary_path == Path("/custom/path/llama-server")

    @patch("sigmahqrag.services.llama.client.subprocess.Popen")
    @patch("sigmahqrag.services.llama.client.LlamaService.health_check")
    def test_start_server(self, mock_health, mock_popen):
        """Test server start."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process
        mock_health.return_value = True

        from sigmahqrag.services.llama import LlamaService

        service = LlamaService(binary_path=Path("/bin/llama-server"))
        result = service.start()

        assert result == mock_process
        mock_popen.assert_called_once()

    @patch("sigmahqrag.services.llama.client.subprocess.Popen")
    def test_stop_server(self, mock_popen):
        """Test server stop."""
        mock_process = MagicMock()
        mock_process.poll.return_value = None
        mock_popen.return_value = mock_process

        from sigmahqrag.services.llama import LlamaService

        service = LlamaService(binary_path=Path("/bin/llama-server"))
        service._process = mock_process
        service.stop()

        mock_process.terminate.assert_called_once()
        assert service._process is None

    @patch("sigmahqrag.services.llama.client.subprocess.run")
    def test_version(self, mock_run):
        """Test version retrieval."""
        mock_run.return_value = MagicMock(stdout="llama.cpp version 1.0.0\n")

        from sigmahqrag.services.llama import LlamaService

        service = LlamaService(binary_path=Path("/bin/llama-server"))
        version = service.version()

        assert "1.0.0" in version

    @patch("sigmahqrag.services.llama.client.urllib.request.urlopen")
    def test_health_check_running(self, mock_urlopen):
        """Test health check when server is running."""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_response

        from sigmahqrag.services.llama import LlamaService

        service = LlamaService(binary_path=Path("/bin/llama-server"))
        assert service.health_check() is True

    @patch("sigmahqrag.services.llama.client.urllib.request.urlopen")
    def test_health_check_not_running(self, mock_urlopen):
        """Test health check when server is not running."""
        mock_urlopen.side_effect = Exception("Connection refused")

        from sigmahqrag.services.llama import LlamaService

        service = LlamaService(binary_path=Path("/bin/llama-server"))
        assert service.health_check() is False

    def test_is_running(self):
        """Test is_running property."""
        from sigmahqrag.services.llama import LlamaService

        service = LlamaService(binary_path=Path("/bin/llama-server"))
        assert service.is_running is False

        mock_process = MagicMock()
        mock_process.poll.return_value = None
        service._process = mock_process
        assert service.is_running is True

        mock_process.poll.return_value = 1
        assert service.is_running is False


class TestBinaryPath:
    """Test binary path functions."""

    @patch("sigmahqrag.services.llama.download.Path.exists")
    def test_get_binary_path_not_found(self, mock_exists):
        """Test get_binary_path raises error when binary not found."""
        mock_exists.return_value = False

        from sigmahqrag.services.llama.download import get_binary_path

        with pytest.raises(FileNotFoundError):
            get_binary_path(Path("/fake/bin"))

    def test_get_binary_path_found(self, tmp_path):
        """Test get_binary_path returns path when binary exists."""
        binary_name = "llama-server.exe" if platform.system() == "Windows" else "llama-server"
        binary = tmp_path / binary_name
        binary.touch()

        from sigmahqrag.services.llama.download import get_binary_path

        result = get_binary_path(tmp_path)
        assert result == binary
