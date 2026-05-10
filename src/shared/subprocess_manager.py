"""Subprocess management utilities."""

from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ServiceProcess:
    """Service process information."""

    name: str
    process: subprocess.Popen[str] | None = None
    pid: int | None = None
    log_file: Path | None = None
    log_handle: Any = None
    is_running: bool = False


class SubprocessManager:
    """Manage background services."""

    def __init__(
        self,
        logs_dir: Path,
        pid_dir: Path,
    ) -> None:
        """Initialize subprocess manager.

        Args:
            logs_dir: Directory for log files
            pid_dir: Directory for PID files
        """
        self.logs_dir = Path(logs_dir)
        self.pid_dir = Path(pid_dir)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.pid_dir.mkdir(parents=True, exist_ok=True)

        self._processes: dict[str, ServiceProcess] = {}
        self._sync_from_pid_files()

    def _sync_from_pid_files(self) -> None:
        """Sync process state from PID files (for orphan detection)."""
        for pid_file in self.pid_dir.glob("*.pid"):
            service_name = pid_file.stem
            try:
                pid = int(pid_file.read_text().strip())
                if self._is_process_running(pid):
                    self._processes[service_name] = ServiceProcess(
                        name=service_name, pid=pid, is_running=True
                    )
                else:
                    pid_file.unlink()
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
            os.kill(pid, 0)
            return True
        except (OSError, ProcessLookupError):
            return False

    async def start_service(
        self,
        name: str,
        cmd: list[str],
        log_file: Path,
        pid_file: Path,
    ) -> dict[str, Any]:
        """Start a service process.

        Args:
            name: Service name
            cmd: Command to run
            log_file: Path to log file
            pid_file: Path to PID file

        Returns:
            Dict with start status
        """
        if name in self._processes and self._processes[name].is_running:
            return {"success": False, "error": f"{name} already running"}

        log_handle = None
        try:
            log_handle = open(log_file, "a")
        except OSError as e:
            return {"success": False, "error": f"Cannot open log file {log_file}: {e}"}

        try:
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
                logger.warning(f"Failed to write PID file for {name}: {e}")

            self._processes[name] = ServiceProcess(
                name=name,
                process=process,
                pid=process.pid,
                log_file=log_file,
                log_handle=log_handle,
                is_running=True,
            )

            logger.info(f"Started {name} (PID: {process.pid})")
            return {
                "success": True,
                "pid": process.pid,
                "log": str(log_file),
            }

        except Exception as e:
            if log_handle:
                try:
                    log_handle.close()
                except OSError:
                    pass
            logger.error(f"Failed to start {name}: {e}")
            return {"success": False, "error": str(e)}

    async def stop_service(self, name: str) -> dict[str, Any]:
        """Stop a service process.

        Args:
            name: Service name

        Returns:
            Dict with stop status
        """
        process_info = self._processes.get(name)
        if (
            not process_info
            or not process_info.is_running
            or process_info.process is None
        ):
            return {"success": False, "error": f"{name} not running"}

        try:
            process_info.process.terminate()

            try:
                process_info.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process_info.process.kill()
                process_info.process.wait()

            if process_info.log_handle is not None:
                process_info.log_handle.close()
                process_info.log_handle = None

            logger.info(f"Stopped {name}")
            process_info.is_running = False
            process_info.process = None
            process_info.pid = None
            del self._processes[name]

            return {"success": True}

        except Exception as e:
            logger.error(f"Failed to stop {name}: {e}")
            return {"success": False, "error": str(e)}

    def get_logs(self, name: str, lines: int = 50) -> str:
        """Get recent log lines for a service.

        Args:
            name: Service name
            lines: Number of lines to return

        Returns:
            Log lines as string
        """
        process_info = self._processes.get(name)
        if not process_info or not process_info.log_file:
            return f"No log file found for {name}"

        log_file = process_info.log_file

        if not log_file.exists():
            return f"Log file {log_file} does not exist"

        try:
            with open(log_file, encoding="utf-8") as f:
                all_lines = f.readlines()
                recent = all_lines[-lines:]
                return "".join(recent)

        except Exception as e:
            return f"Error reading log: {e}"
