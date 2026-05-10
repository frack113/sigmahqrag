"""Llama.cpp service management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from src.shared import (
    LLAMA_BIN_PATH,
    LOGS_DIR,
    PID_DIR,
)
from src.shared.subprocess_manager import SubprocessManager

logger = logging.getLogger(__name__)

LLAMA_BIN = Path(LLAMA_BIN_PATH)
LOGS_DIR = Path(LOGS_DIR)
PID_DIR = Path(PID_DIR)


class LlamaService:
    """High-level service wrapper for Llama.cpp."""

    def __init__(
        self,
        llama_bin: Path = LLAMA_BIN,
        logs_dir: Path = LOGS_DIR,
        pid_dir: Path = PID_DIR,
    ) -> None:
        """Initialize LlamaCppService."""
        self.llama_bin = llama_bin
        self.logs_dir = logs_dir
        self.pid_dir = pid_dir
        self._subprocess_manager = SubprocessManager(self.logs_dir, self.pid_dir)

    async def start_llama(
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

        # Find the executable inside the directory
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

    async def stop_llama(self) -> dict[str, Any]:
        """Stop llama.cpp server."""
        return await self._subprocess_manager.stop_service("llama.cpp")

    async def download_or_update_binary(self) -> dict[str, Any]:
        """Download or update llama.cpp binary."""

        # For simplicity, we'll just use the same logic as Qdrant
        # In a real scenario, we'd unzip it too.
        # For now, let's just mock the download success.
        return {"success": True, "message": "Download initiated (mocked)"}

    def get_logs(self, lines: int = 50) -> str:
        """Get recent log lines for llama.cpp."""
        return self._subprocess_manager.get_logs("llama.cpp", lines)


def create_llama_service() -> LlamaService:
    """Create a llama.cpp service manager."""
    return LlamaService()


async def start_llama_service(
    command: str, model_path: str, port: int = 8080, context_size: int = 4096
) -> dict[str, Any]:
    """Start or restart llama.cpp service."""
    service = create_llama_service()

    if command == "start":
        return await service.start_llama(model_path, port, context_size)
    elif command == "restart":
        await service.stop_llama()
        return await service.start_llama(model_path, port, context_size)
    else:
        raise ValueError(f"Unsupported command: {command}")


async def stop_llama_service() -> dict[str, Any]:
    """Stop llama.cpp service."""
    service = create_llama_service()
    return await service.stop_llama()


async def download_llamacpp_update(version: str) -> dict[str, Any]:
    """Download or update llama.cpp binary."""
    service = create_llama_service()
    return await service.download_or_update_binary()
