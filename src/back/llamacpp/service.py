"""Llama.cpp binary service management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.shared import LLAMA_BIN_PATH, LOGS_DIR, PID_DIR

logger = logging.getLogger(__name__)

LLAMA_BIN = Path(LLAMA_BIN_PATH())
LOGS_DIR = Path(LOGS_DIR)
PID_DIR = Path(PID_DIR)

_llama_service: LlamaBinaryService | None = None


class LlamaBinaryService:
    """Manage llama.cpp binary process (start/stop/logs)."""

    def __init__(
        self,
        llama_bin: Path = LLAMA_BIN,
        logs_dir: Path = LOGS_DIR,
        pid_dir: Path = PID_DIR,
        subprocess_manager=None,
    ) -> None:
        """Initialize LlamaBinaryService."""
        self.llama_bin = llama_bin
        self.logs_dir = logs_dir
        self.pid_dir = pid_dir

        if subprocess_manager is None:
            from src.back.service_manager import get_subprocess_manager

            subprocess_manager = get_subprocess_manager()

        self._subprocess_manager = subprocess_manager

    async def start(
        self,
        model_path: str,
        port: int = 8080,
        context_size: int = 4096,
    ) -> dict[str, Any]:
        """Start llama.cpp server."""
        if not self.llama_bin.exists():
            return {
                "success": False,
                "error": f"llama.cpp directory not found: {self.llama_bin}",
            }

        llama_exe = None
        for exe in self.llama_bin.glob("*.exe"):
            llama_exe = exe
            break

        if not llama_exe:
            return {
                "success": False,
                "error": f"llama.cpp executable not found in {self.llama_bin}",
            }

        log_file = self.logs_dir / "llama.cpp.log"
        pid_file = self.pid_dir / "llama.cpp.pid"

        cmd = [
            str(llama_exe),
            "-m",
            model_path,
            "--port",
            str(port),
            "-c",
            str(context_size),
        ]

        return await self._subprocess_manager.start_service(
            name="llama.cpp",
            cmd=cmd,
            log_file=log_file,
            pid_file=pid_file,
        )

    async def stop(self) -> dict[str, Any]:
        """Stop llama.cpp server."""
        return await self._subprocess_manager.stop_service("llama.cpp")

    def get_logs(self, lines: int = 50) -> str:
        """Get recent log lines for llama.cpp."""
        return self._subprocess_manager.get_logs("llama.cpp", lines)


def create_llama_service() -> LlamaBinaryService:
    """Create or return cached llama service instance."""
    global _llama_service
    if _llama_service is None:
        _llama_service = LlamaBinaryService()
    return _llama_service
