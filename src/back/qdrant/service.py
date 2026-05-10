"""Qdrant service management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import requests

from src.shared import (
    QDRANT_BIN_PATH,
    QDRANT_STORAGE_DIR,
)
from src.shared.subprocess_manager import SubprocessManager

logger = logging.getLogger(__name__)

QDRANT_BIN = Path(QDRANT_BIN_PATH)
QDRANT_STORAGE_DIR = Path(QDRANT_STORAGE_DIR)


class QdrantService:
    """High-level service wrapper for Qdrant."""

    def __init__(
        self,
        qdrant_bin: Path = QDRANT_BIN,
        logs_dir: Path = Path("src/logs"),
        pid_dir: Path = Path("src/data/pids"),
    ) -> None:
        """Initialize QdrantService."""
        self.qdrant_bin = qdrant_bin
        self.logs_dir = logs_dir
        self.pid_dir = pid_dir
        self._subprocess_manager = SubprocessManager(self.logs_dir, self.pid_dir)

    async def start_qdrant(
        self,
        storage_path: str = str(QDRANT_STORAGE_DIR),
        config_path: str = "data/config/qdrant.yaml",
    ) -> dict[str, Any]:
        """Start Qdrant server."""
        qdrant_path = self.qdrant_bin
        if qdrant_path.is_dir():
            exe_in_dir = qdrant_path / "qdrant.exe"
            if exe_in_dir.exists():
                qdrant_path = exe_in_dir
        elif qdrant_path.suffix == "":
            qdrant_path_exe = qdrant_path.with_suffix(".exe")
            if qdrant_path_exe.exists():
                qdrant_path = qdrant_path_exe

        if not qdrant_path.exists() or qdrant_path.is_dir():
            return {
                "success": False,
                "error": f"Qdrant binary not found: {qdrant_path}",
            }

        log_file = self.logs_dir / "qdrant.log"
        pid_file = self.pid_dir / "qdrant.exe.pid"

        cmd = [
            str(qdrant_path),
            "--storage-path",
            storage_path,
            "--config-path",
            config_path,
        ]

        return await self._subprocess_manager.start_service(
            name="qdrant",
            cmd=cmd,
            log_file=log_file,
            pid_file=pid_file,
        )

    async def stop_qdrant(self) -> dict[str, Any]:
        """Stop Qdrant server."""
        return await self._subprocess_manager.stop_service("qdrant")

    async def download_or_update_binary(self) -> dict[str, Any]:
        """Download or update Qdrant binary."""
        download_url = (
            "https://github.com/qdrant/qdrant/releases/latest/download/qdrant.exe"
        )

        result = {"success": True}
        try:
            response = requests.get(download_url, stream=True)
            if response.status_code == 200:
                with open(self.qdrant_bin, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                logger.info(f"Downloaded Qdrant to {self.qdrant_bin}")
            else:
                result["success"] = False
                result["error"] = (
                    f"Failed to download Qdrant: HTTP {response.status_code}"
                )
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)

        return result

    def get_logs(self, lines: int = 50) -> str:
        """Get recent log lines for qdrant."""
        return self._subprocess_manager.get_logs("qdrant", lines)


def create_qdrant_service() -> QdrantService:
    """Create a qdrant service manager."""
    return QdrantService()


async def start_qdrant_service(command: str) -> dict[str, Any]:
    """Start or restart Qdrant service."""
    service = create_qdrant_service()

    if command == "start":
        return await service.start_qdrant(storage_path=str(QDRANT_STORAGE_DIR))
    elif command == "restart":
        await service.stop_qdrant()
        return await service.start_qdrant(storage_path=str(QDRANT_STORAGE_DIR))
    else:
        raise ValueError(f"Unsupported command: {command}")


async def stop_qdrant_service() -> dict[str, Any]:
    """Stop Qdrant service."""
    service = create_qdrant_service()
    return await service.stop_qdrant()


async def download_qdrant_update(version: str) -> dict[str, Any]:
    """Download or update Qdrant binary."""
    service = create_qdrant_service()
    return await service.download_or_update_binary()
