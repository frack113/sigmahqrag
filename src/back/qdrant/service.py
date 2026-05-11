"""Qdrant binary service management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.shared import QDRANT_BIN_PATH

logger = logging.getLogger(__name__)

QDRANT_BIN = QDRANT_BIN_PATH()

_qdrant_service: QdrantBinaryService | None = None


class QdrantBinaryService:
    """Manage Qdrant binary process (start/stop/logs)."""

    def __init__(
        self,
        qdrant_bin: Path = QDRANT_BIN,
        logs_dir: Path = Path("data/logs"),
        pid_dir: Path = Path("data/pids"),
        subprocess_manager=None,
    ) -> None:
        """Initialize QdrantBinaryService."""
        self.qdrant_bin = qdrant_bin
        self.logs_dir = logs_dir
        self.pid_dir = pid_dir

        if subprocess_manager is None:
            from src.back.service_manager import get_subprocess_manager

            subprocess_manager = get_subprocess_manager()

        self._subprocess_manager = subprocess_manager

    async def start(
        self,
        config_path: str = "data/config/qdrant.yaml",
    ) -> dict[str, Any]:
        """Start Qdrant server using config file."""
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

        cmd = [str(qdrant_path)]
        if Path(config_path).exists():
            cmd.extend(["--config-path", config_path])

        return await self._subprocess_manager.start_service(
            name="qdrant",
            cmd=cmd,
            log_file=log_file,
            pid_file=pid_file,
        )

    async def stop(self) -> dict[str, Any]:
        """Stop Qdrant server."""
        return await self._subprocess_manager.stop_service("qdrant")

    def get_logs(self, lines: int = 50) -> str:
        """Get recent log lines for qdrant."""
        return self._subprocess_manager.get_logs("qdrant", lines)


def create_qdrant_service() -> QdrantBinaryService:
    """Create or return cached qdrant service instance."""
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantBinaryService()
    return _qdrant_service
