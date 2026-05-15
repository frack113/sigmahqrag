"""Temporary file management for downloads."""

from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class TempManager:
    """Manager for temporary download files."""

    def __init__(self, temp_dir: Path | None = None) -> None:
        """Initialize temp manager.

        Args:
            temp_dir: Directory for temporary files
        """
        self.temp_dir = temp_dir or Path("temp")

    def create_temp_file(self, download_id: str, extension: str = ".tmp") -> Path:
        """Create a temporary file for downloading.

        Args:
            download_id: Unique download identifier
            extension: File extension

        Returns:
            Path to temporary file
        """
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        return self.temp_dir / f"{download_id}{extension}"

    def cleanup(self, temp_path: Path) -> bool:
        """Clean up a temporary file.

        Args:
            temp_path: Path to temporary file

        Returns:
            True if cleaned up successfully
        """
        try:
            if temp_path.exists():
                os.remove(temp_path)
                logger.info(f"Cleaned up temp file: {temp_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to clean up temp file {temp_path}: {e}")
            return False

    def cleanup_all(self) -> int:
        """Clean up all temporary files.

        Returns:
            Number of files cleaned up
        """
        if not self.temp_dir.exists():
            return 0

        count = 0
        for temp_file in self.temp_dir.iterdir():
            try:
                if temp_file.is_file():
                    os.remove(temp_file)
                    count += 1
            except Exception as e:
                logger.warning(f"Failed to remove {temp_file}: {e}")

        return count


_temp_manager: TempManager | None = None


def create_temp_manager() -> TempManager:
    """Create a singleton temp manager instance."""
    global _temp_manager
    if _temp_manager is None:
        from src.shared.config import TEMP_DIR

        _temp_manager = TempManager(temp_dir=TEMP_DIR)
    return _temp_manager
