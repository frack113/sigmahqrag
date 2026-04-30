"""Service management utilities."""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.config import LLAMA_BIN_PATH, QDRANT_BIN_PATH, LOGS_DIR, DATA_DIR, QDRANT_STORAGE_DIR

logger = logging.getLogger(__name__)

LOGS_DIR = Path(LOGS_DIR)
LLAMA_BIN = str(LLAMA_BIN_PATH)
QDRANT_BIN = str(QDRANT_BIN_PATH)
PID_DIR = DATA_DIR / "pids"


@dataclass
class ServiceProcess:
    """Service process information."""

    name: str
    process: subprocess.Popen[str] | None = None
    pid: int | None = None
    log_file: Path | None = None
    log_handle: Any = None
    is_running: bool = False


class ServiceManager:
    """Manage background services."""

    def __init__(
        self,
        llama_bin: str = LLAMA_BIN,
        qdrant_bin: str = QDRANT_BIN,
        logs_dir: str = LOGS_DIR,
        pid_dir: str = PID_DIR,
    ) -> None:
        """Initialize service manager.

        Args:
            llama_bin: Path to llama.cpp binary
            qdrant_bin: Path to Qdrant binary
            logs_dir: Directory for log files
            pid_dir: Directory for PID files
        """
        self.llama_bin = Path(llama_bin)
        self.qdrant_bin = Path(qdrant_bin)
        self.logs_dir = Path(logs_dir)
        self.pid_dir = Path(pid_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.pid_dir.mkdir(parents=True, exist_ok=True)

        self._llama_process: ServiceProcess = ServiceProcess(name="llama.cpp")
        self._qdrant_process: ServiceProcess = ServiceProcess(name="qdrant")

        self._sync_from_pid_files()

    def _sync_from_pid_files(self) -> None:
        """Sync process state from PID files (for orphan detection)."""
        llama_pid = self.pid_dir / "llama.cpp.pid"
        qdrant_pid = self.pid_dir / "qdrant.pid"

        if llama_pid.exists():
            try:
                pid = int(llama_pid.read_text().strip())
                if self._is_process_running(pid):
                    self._llama_process.is_running = True
                    self._llama_process.pid = pid
                else:
                    llama_pid.unlink()
            except (ValueError, OSError):
                pass

        if qdrant_pid.exists():
            try:
                pid = int(qdrant_pid.read_text().strip())
                if self._is_process_running(pid):
                    self._qdrant_process.is_running = True
                    self._qdrant_process.pid = pid
                else:
                    qdrant_pid.unlink()
            except (ValueError, OSError):
                pass

    def _is_process_running(self, pid: int) -> bool:
        """Check if a process is running.

        Args:
            pid: Process ID

        Returns:
            True if process is running
        """
        try:
            import os

            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    async def start_llama(
        self,
        model_path: str,
        port: int = 8080,
        context_size: int = 4096,
    ) -> dict[str, Any]:
        """Start llama.cpp server.

        Args:
            model_path: Path to model file
            port: Port to listen on
            context_size: Context size in tokens

        Returns:
            Dict with start status
        """
        if self._llama_process.is_running:
            return {"success": False, "error": "llama.cpp already running"}

        if not self.llama_bin.exists():
            return {
                "success": False,
                "error": f"llama.cpp binary not found: {self.llama_bin}",
            }

        log_file = self.logs_dir / "llama.cpp.log"
        pid_file = self.pid_dir / "llama.cpp.pid"

        log_handle = None
        try:
            log_handle = open(log_file, "a")
        except OSError as e:
            return {"success": False, "error": f"Cannot open log file {log_file}: {e}"}

        try:
            cmd = [
                str(self.llama_bin),
                "-m",
                model_path,
                "--port",
                str(port),
                "-c",
                str(context_size),
            ]

            process = subprocess.Popen(
                cmd,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
            )

            if process.pid is None:
                process.kill()
                log_handle.close()
                return {"success": False, "error": "Failed to get process PID"}

            try:
                pid_file.write_text(str(process.pid))
            except OSError as e:
                logger.warning(f"Failed to write PID file: {e}")

            self._llama_process = ServiceProcess(
                name="llama.cpp",
                process=process,
                pid=process.pid,
                log_file=log_file,
                log_handle=log_handle,
                is_running=True,
            )

            logger.info(f"Started llama.cpp (PID: {process.pid})")
            return {
                "success": True,
                "pid": process.pid,
                "log": str(log_file),
                "port": port,
            }

        except Exception as e:
            if log_handle:
                try:
                    log_handle.close()
                except OSError:
                    pass
            logger.error(f"Failed to start llama.cpp: {e}")
            return {"success": False, "error": str(e)}

    async def stop_llama(self) -> dict[str, Any]:
        """Stop llama.cpp server.

        Returns:
            Dict with stop status
        """
        return await self._stop_service(self._llama_process, "llama.cpp")

    async def start_qdrant(
        self,
        storage_path: str = str(QDRANT_STORAGE_DIR),
    ) -> dict[str, Any]:
        """Start Qdrant server.

        Args:
            storage_path: Path to storage directory

        Returns:
            Dict with start status
        """
        if self._qdrant_process.is_running:
            return {"success": False, "error": "Qdrant already running"}

        if not self.qdrant_bin.exists():
            return {
                "success": False,
                "error": f"Qdrant binary not found: {self.qdrant_bin}",
            }

        log_file = self.logs_dir / "qdrant.log"
        pid_file = self.pid_dir / "qdrant.pid"

        log_handle = None
        try:
            log_handle = open(log_file, "a")
        except OSError as e:
            return {"success": False, "error": f"Cannot open log file {log_file}: {e}"}

        try:
            cmd = [
                str(self.qdrant_bin),
                "--storage",
                storage_path,
            ]

            process = subprocess.Popen(
                cmd,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
            )

            if process.pid is None:
                process.kill()
                log_handle.close()
                return {"success": False, "error": "Failed to get process PID"}

            try:
                pid_file.write_text(str(process.pid))
            except OSError as e:
                logger.warning(f"Failed to write PID file: {e}")

            self._qdrant_process = ServiceProcess(
                name="qdrant",
                process=process,
                pid=process.pid,
                log_file=log_file,
                log_handle=log_handle,
                is_running=True,
            )

            logger.info(f"Started Qdrant (PID: {process.pid})")
            return {"success": True, "pid": process.pid, "log": str(log_file)}

        except Exception as e:
            if log_handle:
                try:
                    log_handle.close()
                except OSError:
                    pass
            logger.error(f"Failed to start Qdrant: {e}")
            return {"success": False, "error": str(e)}

    async def stop_qdrant(self) -> dict[str, Any]:
        """Stop Qdrant server.

        Returns:
            Dict with stop status
        """
        return await self._stop_service(self._qdrant_process, "qdrant")

    async def _stop_service(
        self,
        service_proc: ServiceProcess,
        name: str,
    ) -> dict[str, Any]:
        """Stop a service process.

        Args:
            service_proc: ServiceProcess to stop
            name: Service name for logging

        Returns:
            Dict with stop status
        """
        if not service_proc.is_running or service_proc.process is None:
            return {"success": False, "error": f"{name} not running"}

        try:
            service_proc.process.terminate()

            try:
                service_proc.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                service_proc.process.kill()
                service_proc.process.wait()

            if service_proc.log_handle is not None:
                service_proc.log_handle.close()
                service_proc.log_handle = None

            logger.info(f"Stopped {name}")
            service_proc.is_running = False
            service_proc.process = None
            service_proc.pid = None

            return {"success": True}

        except Exception as e:
            logger.error(f"Failed to stop {name}: {e}")
            return {"success": False, "error": str(e)}

    def get_logs(self, service_name: str, lines: int = 50) -> str:
        """Get recent log lines for a service.

        Args:
            service_name: Name of service (llama.cpp or qdrant)
            lines: Number of lines to return

        Returns:
            Log lines as string
        """
        log_file = self.logs_dir / f"{service_name}.log"

        if not log_file.exists():
            return f"No log file found for {service_name}"

        try:
            with open(log_file, encoding="utf-8") as f:
                all_lines = f.readlines()
                recent = all_lines[-lines:]
                return "".join(recent)

        except Exception as e:
            return f"Error reading log: {e}"


def create_service_manager(
    llama_bin: str = LLAMA_BIN,
    qdrant_bin: str = QDRANT_BIN,
    logs_dir: str = LOGS_DIR,
) -> ServiceManager:
    """Create a service manager.

    Args:
        llama_bin: Path to llama.cpp binary
        qdrant_bin: Path to Qdrant binary
        logs_dir: Directory for logs

    Returns:
        ServiceManager instance
    """
    return ServiceManager(llama_bin, qdrant_bin, logs_dir)
