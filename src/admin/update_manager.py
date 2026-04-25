"""Update manager for applying updates with rollback capability."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any

from src.admin.backup_manager import (
    BackupManager,
    create_backup_manager,
)
from src.admin.health import HealthChecker, create_health_checker
from src.exceptions import UpdateError

logger = logging.getLogger(__name__)


class UpdateService:
    """Service for applying updates with rollback capability."""

    def __init__(
        self,
        backup_manager: BackupManager | None = None,
        health_checker: HealthChecker | None = None,
    ) -> None:
        """Initialize update service.

        Args:
            backup_manager: Manager for backups
            health_checker: Manager for health checks
        """
        self.backup_manager = backup_manager or create_backup_manager()
        self.health_checker = health_checker or create_health_checker()

    async def apply_update(
        self,
        service: str,
        version: str,
        binary_path: Path,
    ) -> dict[str, Any]:
        """Apply an update.

        Args:
            service: Service name (llama.cpp, qdrant)
            version: Version to apply
            binary_path: Path to the new binary

        Returns:
            Dict with update result

        Raises:
            UpdateError: If update fails
        """
        if service not in ("llama.cpp", "qdrant"):
            raise UpdateError(f"Unsupported service: {service}")

        current_version = self.backup_manager.get_current_version(service)

        try:
            backup = await self.backup_manager.create_backup(
                service, current_version
            )
            backup_id = backup.backup_id
        except Exception as e:
            logger.warning(f"Backup creation failed: {e}")
            backup_id = None

        target_binary = self.backup_manager.get_binary_path(service)

        try:
            shutil.copy2(binary_path, target_binary)
        except OSError as e:
            error_msg = f"Failed to apply binary: {e}"
            logger.error(error_msg)

            if backup_id:
                await self._perform_rollback(service, backup_id)

            raise UpdateError(error_msg)

        health_result = await self._check_service_health(service)

        if not health_result:
            error_msg = "Health check failed after update"
            logger.error(error_msg)

            if backup_id:
                await self._perform_rollback(service, backup_id)

            return {
                "status": "failed",
                "service": service,
                "version": version,
                "backup_id": backup_id,
                "previous_version": current_version,
                "error": error_msg,
                "rollback": "automatic",
            }

        await self.backup_manager.update_version_metadata(service, version)

        return {
            "status": "success",
            "service": service,
            "version": version,
            "backup_id": backup_id,
            "previous_version": current_version,
            "health_check": "passed",
        }

    async def rollback(
        self,
        service: str,
        backup_id: str | None = None,
    ) -> dict[str, Any]:
        """Rollback to previous version.

        Args:
            service: Service name
            backup_id: Specific backup to restore (optional)

        Returns:
            Dict with rollback result

        Raises:
            UpdateError: If rollback fails
        """
        if service not in ("llama.cpp", "qdrant"):
            raise UpdateError(f"Unsupported service: {service}")

        try:
            metadata, restored_path = await self.backup_manager.restore_backup(
                service, backup_id
            )
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {
                "status": "failed",
                "service": service,
                "error": str(e),
            }

        health_result = await self._check_service_health(service)

        if not health_result:
            logger.error("Health check failed after rollback")
            return {
                "status": "failed",
                "service": service,
                "version": metadata.version,
                "backup_id": metadata.backup_id,
                "health_check": "failed",
            }

        await self.backup_manager.update_version_metadata(
            service, metadata.version
        )

        return {
            "status": "success",
            "service": service,
            "version": metadata.version,
            "backup_id": metadata.backup_id,
            "health_check": "passed",
        }

    async def _perform_rollback(self, service: str, backup_id: str) -> None:
        """Perform automatic rollback.

        Args:
            service: Service name
            backup_id: Backup ID to rollback to
        """
        try:
            await self.backup_manager.restore_backup(service, backup_id)
            logger.info(f"Automatic rollback completed: {backup_id}")
        except Exception as e:
            logger.error(f"Automatic rollback failed: {e}")

    async def _check_service_health(self, service: str) -> bool:
        """Check service health.

        Args:
            service: Service name

        Returns:
            True if healthy
        """
        try:
            if service == "llama.cpp":
                health = await self.health_checker.check_llama()
            elif service == "qdrant":
                health = await self.health_checker.check_qdrant()
            else:
                return False

            return health.status.name == "RUNNING"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def get_status(self) -> dict[str, Any]:
        """Get update system status.

        Returns:
            Dict with current versions and available backups
        """
        from datetime import datetime

        from src.schemas.update import BackupInfo, ServiceVersionInfo

        services_status = {}

        for service in ("llama.cpp", "qdrant"):
            version = self.backup_manager.get_current_version(service)
            version_info = ServiceVersionInfo(
                current_version=version or "unknown",
                last_updated=datetime.now() if version else None,
            )
            services_status[service.replace(".", "_")] = version_info

        all_backups = []
        for service in ("llama.cpp", "qdrant"):
            backups = await self.backup_manager.list_backups(service)
            for backup in backups:
                all_backups.append(
                    BackupInfo(
                        backup_id=backup.backup_id,
                        service=backup.service,
                        version=backup.version,
                        created=backup.created,
                        size_bytes=backup.size_bytes,
                    )
                )

        return {
            "services": services_status,
            "available_backups": all_backups,
        }


_update_service: UpdateService | None = None


def create_update_service() -> UpdateService:
    """Create an update service instance."""
    global _update_service
    if _update_service is None:
        _update_service = UpdateService()
    return _update_service
