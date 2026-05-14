"""Llama.cpp binary service management."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.shared import Config

_llama_service: LlamaBinaryService | None = None


class LlamaBinaryService:
    """Manage llama.cpp binary process (start/stop/logs)."""

    def __init__(
        self,
        config: Config | None = None,
        subprocess_manager=None,
    ) -> None:
        """Initialize LlamaBinaryService."""
        from src.shared import get_config

        self._config = config or get_config()
        self.llama_bin = Path(self._config.llama_binary_path).resolve()
        self.logs_dir = Path(self._config.paths_logs_dir).resolve()
        self.pid_dir = Path(
            self._config.paths_logs_dir.replace("logs", "pids")
        ).resolve()

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

        preferred = self.llama_bin / "llama-server.exe"
        if preferred.exists():
            llama_exe = preferred
        else:
            llama_exe = None
            for exe in self.llama_bin.glob("llama-server*"):
                llama_exe = exe
                break

        if not llama_exe:
            return {
                "success": False,
                "error": (
                    f"llama-server executable not found in {self.llama_bin}. "
                    "Expected llama-server.exe (the OpenAI-compatible HTTP "
                    "server), not llama-cli / llama-batched-bench / etc. — "
                    "first-alphabetical exe selection used to spawn the "
                    "wrong binary and produced 'invalid argument: --port'."
                ),
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
            cwd=self.llama_bin,
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
