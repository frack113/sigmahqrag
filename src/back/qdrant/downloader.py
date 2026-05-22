"""Qdrant download and installation service."""

from __future__ import annotations

import logging
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

QDRANT_BINARY_VERSION = "1.17.1"
QDRANT_UI_VERSION = "v0.2.11"

QDRANT_DOWNLOAD_BASE = (
    f"https://github.com/qdrant/qdrant/releases/download/v{QDRANT_BINARY_VERSION}"
)
QDRANT_UI_DOWNLOAD_URL = (
    f"https://github.com/qdrant/qdrant-web-ui/releases/download/{QDRANT_UI_VERSION}/dist-qdrant.zip"
)

QDRANT_BIN_DIR = Path("data/bin/qdrant")
QDRANT_STATIC_DIR = Path("data/bin/qdrant/static")
QDRANT_UI_DEST = Path("data/bin/qdrant/static")


class QdrantInstallerService:
    """Service for downloading/installing Qdrant binary and web UI."""

    def __init__(
        self,
        bin_dir: Path = QDRANT_BIN_DIR,
        static_dir: Path = QDRANT_STATIC_DIR,
    ) -> None:
        self.bin_dir = bin_dir
        self.static_dir = static_dir

    def get_binary_path(self) -> Path:
        return self.bin_dir / "qdrant.exe"

    def get_ui_dist_path(self) -> Path:
        return self.static_dir / "dist"

    def _safe_extract_zip(self, zip_path: Path, dest_dir: Path) -> None:
        """Extract a zip file safely, preventing path traversal.

        Rejects any archive entry with absolute paths or path traversal
        sequences (e.g. ``/etc/passwd``, ``../../foo``), raising
        ``ValueError`` on the first offending entry.
        """
        dest_resolved = dest_dir.resolve()
        with zipfile.ZipFile(zip_path, "r") as z:
            for name in z.namelist():
                # Prevent absolute paths and path traversal in archive entries
                if os.path.isabs(name) or ".." in name:
                    raise ValueError(
                        f"Zip entry '{name}' would extract outside destination directory"
                    )
            z.extractall(dest_dir)

    async def download_binary(self, progress_callback=None) -> dict[str, Any]:
        """Download Qdrant binary for Windows x86_64."""
        import urllib.request

        self.bin_dir.mkdir(parents=True, exist_ok=True)

        binary_url = f"{QDRANT_DOWNLOAD_BASE}/qdrant-x86_64-pc-windows-msvc.zip"
        zip_path = self.bin_dir / "qdrant.zip"
        binary_path = self.get_binary_path()

        try:
            if progress_callback:
                progress_callback(5, "Downloading binary...")

            urllib.request.urlretrieve(binary_url, zip_path)

            if progress_callback:
                progress_callback(50, "Extracting binary...")

            self._safe_extract_zip(zip_path, self.bin_dir)

            if progress_callback:
                progress_callback(80, "Cleaning up...")

            zip_path.unlink()

            for f in self.bin_dir.glob("qdrant.exe"):
                if f != binary_path:
                    shutil.move(str(f), str(binary_path))

            if progress_callback:
                progress_callback(100, "Binary installed")

            return {
                "success": True,
                "binary_version": QDRANT_BINARY_VERSION,
                "path": str(binary_path),
            }
        except Exception as e:
            logger.error(f"Failed to download Qdrant binary: {e}")
            return {"success": False, "error": str(e)}

    async def download_web_ui(self, progress_callback=None) -> dict[str, Any]:
        """Download Qdrant Web UI (dist-qdrant.zip)."""
        import urllib.request

        QDRANT_UI_DEST.mkdir(parents=True, exist_ok=True)

        zip_path = self.static_dir / "dist-qdrant.zip"

        try:
            if progress_callback:
                progress_callback(5, "Downloading web UI...")

            urllib.request.urlretrieve(QDRANT_UI_DOWNLOAD_URL, zip_path)

            if progress_callback:
                progress_callback(50, "Extracting web UI...")

            self._safe_extract_zip(zip_path, QDRANT_UI_DEST)

            if progress_callback:
                progress_callback(90, "Cleaning up...")

            zip_path.unlink()

            if progress_callback:
                progress_callback(100, "Web UI installed")

            return {
                "success": True,
                "ui_version": QDRANT_UI_VERSION,
                "path": str(QDRANT_UI_DEST),
            }
        except Exception as e:
            logger.error(f"Failed to download Qdrant web UI: {e}")
            return {"success": False, "error": str(e)}

    async def install_all(self, progress_callback=None) -> dict[str, Any]:
        """Download and install both binary and web UI."""
        binary_result = await self.download_binary(progress_callback)
        ui_result = await self.download_web_ui(progress_callback)

        return {
            "success": binary_result.get("success") and ui_result.get("success"),
            "binary": binary_result,
            "web_ui": ui_result,
        }


def create_qdrant_installer() -> QdrantInstallerService:
    return QdrantInstallerService()
