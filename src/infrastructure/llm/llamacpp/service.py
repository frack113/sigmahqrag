"""Llama.cpp binary service management."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.config.settings import Config

logger = logging.getLogger(__name__)

_llama_service: LlamaBinaryService | None = None

_OPENVINO_LIB_PATHS = [
    "/opt/intel/openvino/runtime/lib/intel64",
    "/opt/intel/openvino/runtime/lib",
    "/usr/lib/x86_64-linux-gnu/openvino",
    "/usr/lib/openvino",
    "/usr/local/lib/openvino",
]


def _check_missing_libraries(
    binary: Path,
) -> tuple[dict[str, str] | None, list[str]]:
    """Check binary for missing shared library dependencies.

    Runs ``ldd`` on *binary* to find any unresolved shared libraries.
    For ``libopenvino`` specifically, searches common installation paths.

    Returns:
        Tuple of ``(env_updates, unresolvable)``:
        - ``env_updates`` — dict with ``LD_LIBRARY_PATH`` if OpenVINO was
          resolved, ``None`` otherwise.
        - ``unresolvable`` — list of library names that are still missing
          after all resolution attempts.
    """
    if sys.platform == "win32":
        return None, []

    try:
        result = subprocess.run(
            ["ldd", str(binary)],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None, []

    openvino_missing: list[str] = []
    other_missing: list[str] = []

    for line in result.stdout.splitlines():
        stripped = line.strip()
        if "not found" not in stripped:
            continue
        parts = stripped.split()
        lib_name = parts[0] if parts else stripped
        if "libopenvino" in lib_name:
            openvino_missing.append(lib_name)
        else:
            other_missing.append(lib_name)

    env_updates: dict[str, str] | None = None

    if openvino_missing:
        found_paths: list[str] = []
        for lib_path in _OPENVINO_LIB_PATHS:
            p = Path(lib_path)
            if p.is_dir():
                found_paths.append(str(p.resolve()))
        if found_paths:
            env_updates = {"LD_LIBRARY_PATH": ":".join(found_paths)}
            openvino_missing = []

    unresolvable = openvino_missing + other_missing
    return env_updates, unresolvable


class LlamaBinaryService:
    """Manage llama.cpp binary process (start/stop/logs)."""

    def __init__(
        self,
        config: Config | None = None,
        subprocess_manager=None,
    ) -> None:
        """Initialize LlamaBinaryService."""
        from src.config.settings import get_config

        self._config = config or get_config()
        self.llama_bin = self._config.resolve_llamacpp_bin_path()
        self._llm_dir = Path(self._config.llm_dir).resolve()
        self.logs_dir = Path(self._config.paths_logs_dir).resolve()
        self.pid_dir = Path(self._config.paths_logs_dir.replace("logs", "pids")).resolve()

        if subprocess_manager is None:
            from src.shared.service_manager import get_subprocess_manager

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

        # llama.cpp upstream ships per-OS prebuilt server binaries:
        #   Windows : llama-server.exe
        #   Linux   : llama-server
        #   macOS   : llama-server
        # On Windows prefer .exe, on other platforms prefer the bare name.
        # The previous code globbed `*.exe` and took the first alphabetical
        # match, which spawned `llama-batched-bench.exe` and crashed with
        # "invalid argument: --port"; on Linux/macOS it found nothing at all.
        if sys.platform == "win32":
            candidates = ("llama-server.exe", "llama-server")
        else:
            candidates = ("llama-server", "llama-server.exe")

        llama_exe: Path | None = None
        for name in candidates:
            candidate = self.llama_bin / name
            if candidate.is_file():
                llama_exe = candidate
                break

        if not llama_exe:
            return {
                "success": False,
                "error": (
                    f"llama-server executable not found in {self.llama_bin}. "
                    "Expected the llama.cpp HTTP server binary "
                    "(llama-server / llama-server.exe), not llama-cli / "
                    "llama-batched-bench / etc."
                ),
            }

        model_resolved = Path(model_path).resolve()
        try:
            model_resolved.relative_to(self._llm_dir)
        except ValueError:
            return {
                "success": False,
                "error": f"Model path '{model_path}' is outside the allowed models directory ({self._llm_dir})",
            }

        log_file = self.logs_dir / "llama.cpp.log"
        pid_file = self.pid_dir / "llama.cpp.pid"

        cmd = [
            str(llama_exe),
            "-m",
            str(model_resolved),
            "--port",
            str(port),
            "-c",
            str(context_size),
        ]

        env, missing = _check_missing_libraries(llama_exe)
        if missing:
            logger.warning(
                "llama-server has unresolved library dependencies: %s. "
                "The Linux build is a unified binary that includes all backends "
                "(CUDA, Vulkan, OpenVINO, SYCL, etc.) and requires their "
                "respective runtime libraries. Install the missing packages or "
                "build llama.cpp from source with only the backends you need.",
                ", ".join(missing),
            )
            return {
                "success": False,
                "error": (
                    f"Cannot start llama-server: missing shared libraries "
                    f"({', '.join(missing)}). "
                    "Install the required runtime libraries. For example:\n"
                    "  - OpenVINO: install intel-openvino-runtime\n"
                    "  - CUDA: install cuda-toolkit\n"
                    "  - Vulkan: install vulkan-loader\n"
                    "  - ROCm: install rocm-device-libs"
                ),
            }

        return await self._subprocess_manager.start_service(  # type: ignore[no-any-return]
            name="llama.cpp",
            cmd=cmd,
            log_file=log_file,
            pid_file=pid_file,
            cwd=self.llama_bin,
            env=env,
        )

    async def stop(self) -> dict[str, Any]:
        """Stop llama.cpp server."""
        return await self._subprocess_manager.stop_service("llama.cpp")  # type: ignore[no-any-return]

    def get_logs(self, lines: int = 50) -> str:
        """Get recent log lines for llama.cpp."""
        return self._subprocess_manager.get_logs("llama.cpp", lines)  # type: ignore[no-any-return]


def get_llama_service() -> LlamaBinaryService:
    """Get or create the cached llama service singleton."""
    global _llama_service
    if _llama_service is None:
        _llama_service = LlamaBinaryService()
    return _llama_service
