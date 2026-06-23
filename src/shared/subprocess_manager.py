"""Subprocess management utilities."""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import threading
from collections import deque
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
    pid_file: Path | None = None
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

        self._processes: dict[str, ServiceProcess] = {}
        self._lock = threading.Lock()
        self._sync_from_pid_files()

    def _sync_from_pid_files(self) -> None:
        """Sync process state from PID files (for orphan detection)."""
        for pid_file in self.pid_dir.glob("*.pid"):
            service_name = pid_file.stem
            try:
                pid = int(pid_file.read_text().strip())
                if self._is_process_running(pid):
                    with self._lock:
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

    def _find_process_by_port(self, port: int) -> int | None:
        """Find PID of process listening on a given Windows port.

        Args:
            port: TCP port number

        Returns:
            PID if found, None otherwise
        """
        try:
            import subprocess

            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            for line in result.stdout.splitlines():
                parts = line.split()
                for part in parts:
                    if f":{port}" == part and len(parts) >= 5:
                        try:
                            return int(parts[-1])
                        except (ValueError, IndexError):
                            pass
        except Exception as e:
            logger.warning(f"Could not find process on port {port}: {e}")
        return None

    def is_healthy(self, name: str) -> bool:
        """Check if a service process is healthy (running).

        Args:
            name: Service name

        Returns:
            True if service is running
        """
        with self._lock:
            if name not in self._processes:
                return False
            proc_info = self._processes[name]
            if not proc_info.is_running or proc_info.pid is None:
                return False
            return self._is_process_running(proc_info.pid)

    async def start_service(
        self,
        name: str,
        cmd: list[str],
        log_file: Path,
        pid_file: Path,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Start a service process.

        Args:
            name: Service name
            cmd: Command to run
            log_file: Path to log file
            pid_file: Path to PID file
            cwd: Working directory for subprocess
            env: Optional environment variables for the subprocess

        Returns:
            Dict with start status
        """
        with self._lock:
            if name in self._processes and self._processes[name].is_running:
                return {"success": False, "error": f"{name} already running"}

        log_handle = None
        try:
            log_handle = open(log_file, "a")
        except OSError as e:
            return {"success": False, "error": f"Cannot open log file {log_file}: {e}"}

        proc_env = None
        if env:
            proc_env = os.environ.copy()
            proc_env.update(env)

        try:
            process = subprocess.Popen(
                cmd,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                cwd=str(cwd) if cwd else None,
                env=proc_env,
                text=True,
            )

            if process.pid is None:
                process.kill()
                log_handle.close()
                return {"success": False, "error": "Failed to get process PID"}

            try:
                pid_file.parent.mkdir(parents=True, exist_ok=True)
                pid_file.write_text(str(process.pid))
            except OSError as e:
                logger.warning(f"Failed to write PID file for {name}: {e}")

            with self._lock:
                self._processes[name] = ServiceProcess(
                    name=name,
                    process=process,
                    pid=process.pid,
                    log_file=log_file,
                    pid_file=pid_file,
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
        with self._lock:
            process_info = self._processes.get(name)
            if not process_info or not process_info.is_running:
                if process_info and process_info.log_handle is not None:
                    try:
                        process_info.log_handle.close()
                    except OSError:
                        pass
                self._processes.pop(name, None)
                return {"success": False, "error": f"{name} not running"}

            if process_info.pid is None:
                return {"success": False, "error": f"{name} has no PID"}

        try:
            if process_info.process is not None:
                process_info.process.terminate()
                try:
                    process_info.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process_info.process.kill()
                    try:
                        process_info.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        logger.warning(f"Could not kill {name} (PID {process_info.pid})")
            else:
                if os.name == "nt":
                    try:
                        subprocess.run(
                            ["taskkill", "/F", "/PID", str(process_info.pid)],
                            capture_output=True,
                            timeout=10,
                        )
                    except subprocess.TimeoutExpired:
                        logger.warning(f"taskkill timed out for {name} (PID {process_info.pid})")
                else:
                    try:
                        os.kill(process_info.pid, signal.SIGTERM)
                    except ProcessLookupError:
                        logger.debug(f"{name} (PID {process_info.pid}) already exited")
        except Exception as e:
            logger.error(f"Failed to stop {name}: {e}")
            try:
                if process_info.pid_file:
                    process_info.pid_file.unlink(missing_ok=True)
            except OSError:
                pass
            return {"success": False, "error": str(e)}
        finally:
            if process_info.log_handle is not None:
                try:
                    process_info.log_handle.close()
                except OSError:
                    pass
                process_info.log_handle = None

            logger.info(f"Stopped {name}")
            process_info.is_running = False
            process_info.process = None
            process_info.pid = None
            self._processes.pop(name, None)

            return {"success": True}

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
                recent = deque(f, maxlen=lines)
                return "".join(recent)

        except Exception as e:
            return f"Error reading log: {e}"

    async def stop_all(self) -> dict[str, Any]:
        """Stop all running services (called on app shutdown)."""
        results = {}
        service_names = list(self._processes.keys())

        for name in service_names:
            result = await self.stop_service(name)
            results[name] = result

        logger.info(f"Stopped all services: {list(service_names)}")
        return results

    def shutdown(self) -> None:
        """Synchronous shutdown for all services (called atexit)."""
        for name, proc_info in list(self._processes.items()):
            try:
                if proc_info.process and proc_info.process.poll() is None:
                    proc_info.process.send_signal(
                        signal.SIGTERM
                        if os.name != "nt"
                        else getattr(signal, "CTRL_BREAK_EVENT", signal.SIGTERM)
                    )
                    try:
                        proc_info.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc_info.process.kill()

                if proc_info.log_handle:
                    try:
                        proc_info.log_handle.close()
                    except OSError:
                        pass

                if proc_info.pid_file:
                    try:
                        proc_info.pid_file.unlink(missing_ok=True)
                    except OSError:
                        pass
            except Exception as e:
                logger.error(f"Error shutting down {name}: {e}")

        self._processes.clear()
        logger.info("All services shut down")
