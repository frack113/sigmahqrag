"""Backup manager for service binaries."""

from __future__ import annotations

import json
import logging
import tarfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config import BACKUP_DIR, BIN_DIR, MAX_BACKUPS
from src.exceptions import BackupError

logger = logging.getLogger(__name__)


@dataclass
class BackupMetadata:
    """Metadata for a backup."""

    backup_id: str
    service: str
    version: str
    created: datetime
    files: list[str]
    size_bytes: int
    checksum: str = ""


class BackupManager:
    """Manager for creating and restoring backups."""

    def __init__(
        self,
        backup_dir: Path | None = None,
        max_backups: int = MAX_BACKUPS,
    ) -> None:
        """Initialize backup manager.

        Args:
            backup_dir: Directory for storing backups
            max_backups: Maximum number of backups to retain
        """
        self.backup_dir = backup_dir or BACKUP_DIR
        self.max_backups = max_backups
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure backup directories exist."""
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _get_service_backup_dir(self, service: str) -> Path:
        """Get backup directory for a service.

        Args:
            service: Service name

        Returns:
            Path to service backup directory
        """
        return self.backup_dir / service.replace(".", "-")

    def _generate_backup_id(self, service: str, version: str) -> str:
        """Generate a unique backup ID.

        Args:
            service: Service name
            version: Version

        Returns:
            Backup ID
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        return f"backup-{service.replace('.', '-')}-{version}-{timestamp}"

    def get_binary_path(self, service: str) -> Path:
        """Get the binary path for a service.

        Args:
            service: Service name

        Returns:
            Path to binary
        """
        if service == "llama.cpp":
            return BIN_DIR / "llama-server"
        elif service == "qdrant":
            return BIN_DIR / "qdrant"

        return BIN_DIR / service.replace(".", "-")

    def get_current_version(self, service: str) -> str | None:
        """Get current version from version metadata.

        Args:
            service: Service name

        Returns:
            Version string or None
        """
        version_file = self.backup_dir / "versions.json"
        if not version_file.exists():
            return None

        try:
            data = json.loads(version_file.read_text())
            return data.get(service, {}).get("version")
        except (json.JSONDecodeError, OSError):
            return None

    async def create_backup(
        self, service: str, version: str | None = None
    ) -> BackupMetadata:
        """Create a backup of current binary.

        Args:
            service: Service name
            version: Version to backup (defaults to current version)

        Returns:
            BackupMetadata

        Raises:
            BackupError: If backup fails
        """
        binary_path = self.get_binary_path(service)
        version = version or self.get_current_version(service)

        if not binary_path.exists():
            raise BackupError(f"Binary not found: {binary_path}")

        if not version:
            version = "unknown"

        backup_id = self._generate_backup_id(service, version)
        backup_service_dir = self._get_service_backup_dir(service)
        backup_service_dir.mkdir(parents=True, exist_ok=True)

        backup_archive = backup_service_dir / f"{backup_id}.tar.gz"

        try:
            files_to_backup = []
            with tarfile.open(backup_archive, "w:gz") as tar:
                tar.add(binary_path, arcname=binary_path.name)
                files_to_backup.append(binary_path.name)

            size_bytes = backup_archive.stat().st_size

            metadata = BackupMetadata(
                backup_id=backup_id,
                service=service,
                version=version,
                created=datetime.now(),
                files=files_to_backup,
                size_bytes=size_bytes,
            )

            metadata_file = backup_service_dir / f"{backup_id}.json"
            metadata_file.write_text(
                json.dumps(
                    {
                        "backup_id": metadata.backup_id,
                        "service": metadata.service,
                        "version": metadata.version,
                        "created": metadata.created.isoformat(),
                        "files": metadata.files,
                        "size_bytes": metadata.size_bytes,
                        "checksum": metadata.checksum,
                    },
                    indent=2,
                )
            )

            logger.info(f"Created backup: {backup_id}")
            await self._cleanup_old_backups(service)

            return metadata

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise BackupError(f"Failed to create backup: {e}") from e

    async def restore_backup(
        self, service: str, backup_id: str | None = None
    ) -> tuple[BackupMetadata, Path]:
        """Restore a backup.

        Args:
            service: Service name
            backup_id: Backup ID to restore (defaults to latest)

        Returns:
            Tuple of (BackupMetadata, restored binary path)

        Raises:
            BackupError: If restore fails
        """
        if backup_id:
            metadata = await self._load_backup_metadata(service, backup_id)
        else:
            backups = await self.list_backups(service)
            if not backups:
                raise BackupError(f"No backups found for {service}")

            latest = backups[0]
            metadata = latest

        backup_service_dir = self._get_service_backup_dir(service)
        backup_archive = backup_service_dir / f"{metadata.backup_id}.tar.gz"

        if not backup_archive.exists():
            raise BackupError(f"Backup archive not found: {backup_archive}")

        binary_path = self.get_binary_path(service)

        try:
            with tarfile.open(backup_archive, "r:gz") as tar:
                tar.extractall(BIN_DIR)

            logger.info(f"Restored backup: {metadata.backup_id}")

            return metadata, binary_path

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise BackupError(f"Failed to restore backup: {e}") from e

    async def _load_backup_metadata(
        self, service: str, backup_id: str
    ) -> BackupMetadata:
        """Load backup metadata.

        Args:
            service: Service name
            backup_id: Backup ID

        Returns:
            BackupMetadata

        Raises:
            BackupError: If metadata not found
        """
        backup_service_dir = self._get_service_backup_dir(service)
        metadata_file = backup_service_dir / f"{backup_id}.json"

        if not metadata_file.exists():
            raise BackupError(f"Backup metadata not found: {backup_id}")

        try:
            data = json.loads(metadata_file.read_text())
            return BackupMetadata(
                backup_id=data["backup_id"],
                service=data["service"],
                version=data["version"],
                created=datetime.fromisoformat(data["created"]),
                files=data["files"],
                size_bytes=data["size_bytes"],
                checksum=data.get("checksum", ""),
            )
        except (json.JSONDecodeError, OSError, KeyError) as e:
            raise BackupError(f"Failed to load backup metadata: {e}") from e

    async def list_backups(self, service: str) -> list[BackupMetadata]:
        """List available backups for a service.

        Args:
            service: Service name

        Returns:
            List of BackupMetadata sorted by creation time (newest first)
        """
        backup_service_dir = self._get_service_backup_dir(service)

        if not backup_service_dir.exists():
            return []

        backups = []
        for metadata_file in backup_service_dir.glob("*.json"):
            try:
                data = json.loads(metadata_file.read_text())
                backups.append(
                    BackupMetadata(
                        backup_id=data["backup_id"],
                        service=data["service"],
                        version=data["version"],
                        created=datetime.fromisoformat(data["created"]),
                        files=data["files"],
                        size_bytes=data["size_bytes"],
                        checksum=data.get("checksum", ""),
                    )
                )
            except (json.JSONDecodeError, OSError, KeyError):
                continue

        backups.sort(key=lambda b: b.created, reverse=True)
        return backups

    async def _cleanup_old_backups(self, service: str) -> None:
        """Clean up old backups keeping only max_backups.

        Args:
            service: Service name
        """
        backups = await self.list_backups(service)

        if len(backups) <= self.max_backups:
            return

        backups_to_delete = backups[self.max_backups :]

        for backup in backups_to_delete:
            backup_service_dir = self._get_service_backup_dir(service)
            archive = backup_service_dir / f"{backup.backup_id}.tar.gz"
            metadata = backup_service_dir / f"{backup.backup_id}.json"

            try:
                if archive.exists():
                    archive.unlink()
                if metadata.exists():
                    metadata.unlink()
                logger.info(f"Deleted old backup: {backup.backup_id}")
            except OSError as e:
                logger.warning(f"Failed to delete backup {backup.backup_id}: {e}")

    async def update_version_metadata(
        self, service: str, version: str
    ) -> None:
        """Update version metadata.

        Args:
            service: Service name
            version: Version
        """
        version_file = self.backup_dir / "versions.json"
        data: dict[str, Any] = {}

        if version_file.exists():
            try:
                data = json.loads(version_file.read_text())
            except json.JSONDecodeError:
                pass

        data[service] = {
            "version": version,
            "last_updated": datetime.now().isoformat(),
        }

        version_file.write_text(json.dumps(data, indent=2))


_backup_manager: BackupManager | None = None


def create_backup_manager(
    backup_dir: Path | None = None,
    max_backups: int = MAX_BACKUPS,
) -> BackupManager:
    """Create a backup manager instance.

    Args:
        backup_dir: Directory for backups
        max_backups: Maximum backups to keep

    Returns:
        BackupManager instance
    """
    global _backup_manager
    if _backup_manager is None:
        _backup_manager = BackupManager(
            backup_dir=backup_dir,
            max_backups=max_backups,
        )
    return _backup_manager
