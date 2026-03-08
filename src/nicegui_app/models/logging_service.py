"""
Logging Service for SigmaHQ RAG Application

This module provides centralized logging functionality with rotation support
and real-time log viewing capabilities for the NiceGUI application.
"""

import logging
import logging.handlers
import os
import threading
import time
from pathlib import Path
from typing import List, Optional, Callable
from datetime import datetime


class LoggingService:
    """Centralized logging service with rotation and real-time monitoring."""

    def __init__(
        self,
        log_dir: str = "logs",
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
    ):
        """
        Initialize the logging service.

        Args:
            log_dir: Directory to store log files
            max_bytes: Maximum size of each log file before rotation (default: 10MB)
            backup_count: Number of backup log files to keep (default: 5)
        """
        self.log_dir = Path(log_dir)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.log_file = self.log_dir / "app.log"
        self._setup_logging()
        self._log_monitor = None
        self._log_callbacks = []

    def _setup_logging(self):
        """Configure the logging system with rotation."""
        # Create log directory if it doesn't exist
        self.log_dir.mkdir(exist_ok=True)

        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(logging.DEBUG)

        # Clear any existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # File handler with rotation
        file_handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=self.max_bytes,
            backupCount=self.backup_count,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)

        # Add handlers to root logger
        root_logger.addHandler(file_handler)
        root_logger.addHandler(console_handler)

        # Prevent duplicate logs in child loggers
        logging.getLogger("uvicorn").propagate = False
        logging.getLogger("nicegui").propagate = False

        # Log initialization
        logger = logging.getLogger(__name__)
        logger.info(f"Logging service initialized. Log file: {self.log_file}")
        logger.info(
            f"Log rotation: max {self.max_bytes} bytes, {self.backup_count} backups"
        )

    def get_logger(self, name: str) -> logging.Logger:
        """
        Get a logger instance with the specified name.

        Args:
            name: Logger name (typically __name__)

        Returns:
            Configured logger instance
        """
        return logging.getLogger(name)

    def get_recent_logs(self, lines: int = 100) -> List[str]:
        """
        Get recent log entries from the log file.

        Args:
            lines: Number of recent lines to retrieve (default: 100)

        Returns:
            List of log lines
        """
        if not self.log_file.exists():
            return ["No log file found."]

        try:
            with open(self.log_file, "r", encoding="utf-8") as f:
                all_lines = f.readlines()
                return all_lines[-lines:] if len(all_lines) >= lines else all_lines
        except Exception as e:
            return [f"Error reading log file: {e}"]

    def get_log_file_size(self) -> int:
        """
        Get the current size of the log file in bytes.

        Returns:
            File size in bytes
        """
        if self.log_file.exists():
            return self.log_file.stat().st_size
        return 0

    def get_log_file_info(self) -> dict:
        """
        Get information about the log file and rotation.

        Returns:
            Dictionary with log file information
        """
        info = {
            "log_file": str(self.log_file),
            "exists": self.log_file.exists(),
            "size_bytes": self.get_log_file_size(),
            "size_mb": (
                round(self.get_log_file_size() / (1024 * 1024), 2)
                if self.log_file.exists()
                else 0
            ),
            "max_bytes": self.max_bytes,
            "backup_count": self.backup_count,
            "rotation_enabled": True,
        }

        # Check for rotated log files
        rotated_files = []
        for i in range(1, self.backup_count + 1):
            rotated_file = Path(f"{self.log_file}.{i}")
            if rotated_file.exists():
                rotated_files.append(
                    {
                        "file": str(rotated_file),
                        "size_bytes": rotated_file.stat().st_size,
                        "size_mb": round(
                            rotated_file.stat().st_size / (1024 * 1024), 2
                        ),
                    }
                )

        info["rotated_files"] = rotated_files
        return info

    def clear_logs(self) -> bool:
        """
        Clear the current log file.

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.log_file.exists():
                self.log_file.unlink()
                # Recreate the log file by getting a logger
                self.get_logger(__name__).info("Log file cleared and recreated")
                return True
            return True
        except Exception as e:
            self.get_logger(__name__).error(f"Failed to clear logs: {e}")
            return False

    def start_monitoring(self, callback: Callable[[str], None], interval: float = 1.0):
        """
        Start monitoring the log file for new entries.

        Args:
            callback: Function to call with new log lines
            interval: Check interval in seconds (default: 1.0)
        """
        if self._log_monitor and self._log_monitor.is_alive():
            return

        self._log_callbacks.append(callback)

        def monitor_logs():
            last_position = 0
            if self.log_file.exists():
                with open(self.log_file, "r", encoding="utf-8") as f:
                    f.seek(0, 2)  # Go to end of file
                    last_position = f.tell()

            while not threading.current_thread().stopped():
                try:
                    if self.log_file.exists():
                        with open(self.log_file, "r", encoding="utf-8") as f:
                            f.seek(last_position)
                            new_lines = f.readlines()
                            last_position = f.tell()

                            if new_lines:
                                for line in new_lines:
                                    for callback in self._log_callbacks:
                                        callback(line.strip())

                    time.sleep(interval)
                except Exception:
                    time.sleep(interval)

        self._log_monitor = threading.Thread(target=monitor_logs, daemon=True)
        self._log_monitor.start()

    def stop_monitoring(self):
        """Stop monitoring the log file."""
        if self._log_monitor:
            self._log_monitor.stop()
            self._log_monitor = None
        self._log_callbacks.clear()

    def get_log_level(self) -> str:
        """Get the current logging level."""
        return logging.getLevelName(logging.getLogger().level)

    def set_log_level(self, level: str):
        """
        Set the logging level.

        Args:
            level: Logging level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        """
        level = level.upper()
        if level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            logging.getLogger().setLevel(getattr(logging, level))
            self.get_logger(__name__).info(f"Log level changed to: {level}")
        else:
            raise ValueError(f"Invalid log level: {level}")


# Global logging service instance
logging_service = LoggingService()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance using the global logging service.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging_service.get_logger(name)
