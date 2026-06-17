"""Tests for platform-aware Qdrant binary download."""

from __future__ import annotations

import platform
import sys
from pathlib import Path
from unittest.mock import patch

from src.infrastructure.vectorstore.downloader import QDRANT_DOWNLOAD_BASE, QdrantInstallerService


class TestQdrantPlatformDetection:
    def test_windows_x86_64(self) -> None:
        with (
            patch.object(platform, "system", return_value="Windows"),
            patch.object(platform, "machine", return_value="AMD64"),
        ):
            asset = QdrantInstallerService._platform_asset_name()
            assert asset == "x86_64-pc-windows-msvc"

    def test_linux_x86_64(self) -> None:
        with (
            patch.object(platform, "system", return_value="Linux"),
            patch.object(platform, "machine", return_value="x86_64"),
        ):
            asset = QdrantInstallerService._platform_asset_name()
            assert asset == "x86_64-unknown-linux-musl"

    def test_linux_arm64(self) -> None:
        with (
            patch.object(platform, "system", return_value="Linux"),
            patch.object(platform, "machine", return_value="aarch64"),
        ):
            asset = QdrantInstallerService._platform_asset_name()
            assert asset == "aarch64-unknown-linux-musl"

    def test_macos_x86_64(self) -> None:
        with (
            patch.object(platform, "system", return_value="Darwin"),
            patch.object(platform, "machine", return_value="x86_64"),
        ):
            asset = QdrantInstallerService._platform_asset_name()
            assert asset == "x86_64-apple-darwin"

    def test_macos_arm64(self) -> None:
        with (
            patch.object(platform, "system", return_value="Darwin"),
            patch.object(platform, "machine", return_value="arm64"),
        ):
            asset = QdrantInstallerService._platform_asset_name()
            assert asset == "aarch64-apple-darwin"

    def test_binary_url_contains_platform(self) -> None:
        with (
            patch.object(platform, "system", return_value="Linux"),
            patch.object(platform, "machine", return_value="x86_64"),
        ):
            asset = QdrantInstallerService._platform_asset_name()
            url = f"{QDRANT_DOWNLOAD_BASE}/qdrant-{asset}.zip"
            assert "linux-musl" in url

    def test_get_binary_path_windows(self) -> None:
        with patch.object(sys, "platform", "win32"):
            installer = QdrantInstallerService(bin_dir=Path("/fake"))
            assert installer.get_binary_path().name == "qdrant.exe"

    def test_get_binary_path_linux(self) -> None:
        with patch.object(sys, "platform", "linux"):
            installer = QdrantInstallerService(bin_dir=Path("/fake"))
            assert installer.get_binary_path().name == "qdrant"

    def test_get_binary_path_macos(self) -> None:
        with patch.object(sys, "platform", "darwin"):
            installer = QdrantInstallerService(bin_dir=Path("/fake"))
            assert installer.get_binary_path().name == "qdrant"
