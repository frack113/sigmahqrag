"""Tests for version manager."""

from pathlib import Path
from unittest.mock import MagicMock, patch


from src.shared.version_manager import VersionManager, create_version_manager


class TestVersionManagerInit:
    def test_default_init(self) -> None:
        vm = VersionManager()
        assert vm.github_token is None
        assert vm.SERVICE_REPOS["llama.cpp"] == ("ggml-org", "llama.cpp")
        assert vm.SERVICE_REPOS["qdrant"] == ("qdrant", "qdrant")

    def test_with_token(self) -> None:
        vm = VersionManager(github_token="token-123")
        assert vm.github_token == "token-123"


class TestGetHeaders:
    def test_no_token(self) -> None:
        vm = VersionManager()
        headers = vm._get_headers()
        assert headers["Accept"] == "application/vnd.github+json"
        assert "Authorization" not in headers

    def test_with_token(self) -> None:
        vm = VersionManager(github_token="token-123")
        headers = vm._get_headers()
        assert headers["Authorization"] == "Bearer token-123"


class TestDetectPlatform:
    def test_uses_config_os(self) -> None:
        vm = VersionManager()
        mock_config = MagicMock()
        mock_config.os = "linux"
        with patch.object(vm, "_read_os_preference", return_value="linux"):
            os_name, arch, gpu = vm._detect_platform()
            assert os_name == "linux"
            assert arch in ("x64", "arm64")

    def test_detects_windows(self) -> None:
        vm = VersionManager()
        with (
            patch.object(vm, "_read_os_preference", return_value=None),
            patch("platform.system", return_value="Windows"),
            patch("platform.machine", return_value="AMD64"),
        ):
            os_name, arch, gpu = vm._detect_platform()
            assert os_name == "windows"
            assert arch == "x64"

    def test_detects_macos(self) -> None:
        vm = VersionManager()
        with (
            patch.object(vm, "_read_os_preference", return_value=None),
            patch("platform.system", return_value="Darwin"),
            patch("platform.machine", return_value="arm64"),
        ):
            os_name, arch, gpu = vm._detect_platform()
            assert os_name == "macos"
            assert arch == "arm64"

    def test_detects_linux(self) -> None:
        vm = VersionManager()
        with (
            patch.object(vm, "_read_os_preference", return_value=None),
            patch("platform.system", return_value="Linux"),
            patch("platform.machine", return_value="x86_64"),
        ):
            os_name, arch, gpu = vm._detect_platform()
            assert os_name == "linux"
            assert arch == "x64"


def _make_asset(name: str, url: str = "", size: int = 100):
    a = MagicMock()
    a.name = name
    a.browser_download_url = url
    a.size = size
    return a


class TestFindMatchingAsset:
    def test_matches_llamacpp_cpu_on_windows(self) -> None:
        vm = VersionManager()
        release = MagicMock()
        release.assets = [
            _make_asset("llama-b3921-win-cpu-x64.zip"),
        ]
        with patch.object(vm, "_detect_platform", return_value=("windows", "x64", "cpu")):
            asset = vm.find_matching_asset(release, "llama.cpp")
            assert asset is not None
            assert "cpu" in asset.name

    def test_matches_llamacpp_gpu_on_windows(self) -> None:
        vm = VersionManager()
        release = MagicMock()
        release.assets = [
            _make_asset("llama-b3921-win-cuda-12.0-x64.zip"),
            _make_asset("llama-b3921-win-cpu-x64.zip"),
        ]
        with patch.object(vm, "_detect_platform", return_value=("windows", "x64", "cuda")):
            asset = vm.find_matching_asset(release, "llama.cpp")
            assert asset is not None
            assert "cuda" in asset.name

    def test_skips_cudart_assets(self) -> None:
        vm = VersionManager()
        release = MagicMock()
        release.assets = [
            _make_asset("cudart-12.0-win-x64.zip"),
            _make_asset("llama-b3921-win-cpu-x64.zip"),
        ]
        with patch.object(vm, "_detect_platform", return_value=("windows", "x64", None)):
            asset = vm.find_matching_asset(release, "llama.cpp")
            assert asset is not None
            assert "cudart" not in asset.name

    def test_matches_qdrant_windows(self) -> None:
        vm = VersionManager()
        release = MagicMock()
        release.assets = [
            _make_asset("qdrant-x86_64-pc-windows-msvc.zip"),
        ]
        with patch.object(vm, "_detect_platform", return_value=("windows", "x64", None)):
            asset = vm.find_matching_asset(release, "qdrant")
            assert asset is not None

    def test_returns_none_when_no_match(self) -> None:
        vm = VersionManager()
        release = MagicMock()
        release.assets = []
        with patch.object(vm, "_detect_platform", return_value=("windows", "x64", "cpu")):
            asset = vm.find_matching_asset(release, "llama.cpp")
            assert asset is None


class TestGetBinaryName:
    def test_llamacpp(self) -> None:
        vm = VersionManager()
        with patch("src.shared.version_manager.BIN_DIR", Path("/tmp/bin")):
            asset = _make_asset("llama.zip")
            result = vm.get_binary_name("llama.cpp", asset)
            assert "llama-server" in str(result)

    def test_qdrant(self) -> None:
        vm = VersionManager()
        with patch("src.shared.version_manager.BIN_DIR", Path("/tmp/bin")):
            asset = _make_asset("qdrant.zip")
            result = vm.get_binary_name("qdrant", asset)
            assert "qdrant" in str(result)

    def test_other(self) -> None:
        vm = VersionManager()
        with patch("src.shared.version_manager.BIN_DIR", Path("/tmp/bin")):
            asset = _make_asset("other.zip")
            result = vm.get_binary_name("other", asset)
            assert "other.zip" in str(result)


class TestCreateVersionManager:
    def test_creates_instance(self) -> None:
        vm = create_version_manager()
        assert isinstance(vm, VersionManager)

    def test_with_token(self) -> None:
        vm = create_version_manager(github_token="tok")
        assert vm.github_token == "tok"
