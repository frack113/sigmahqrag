"""Update manager for system status and version checks (Story 3.5 - GREEN phase)."""

from __future__ import annotations

import logging
from typing import Any

from src.core.backend.services.health_check import HealthCheckService

logger = logging.getLogger(__name__)


class UpdateService:
    """Service for checking system update status and version information."""

    def __init__(
        self,
        health_checker: HealthCheckService | None = None,
    ) -> None:
        """Initialize update service.

        Args:
            health_checker: Manager for health checks (FR18)
        """
        self.health_checker = health_checker or HealthCheckService()

    async def _check_service_health(self, service: str) -> bool:
        """Check service health.

        Args:
            service: Service name (llama.cpp or qdrant)

        Returns:
            True if healthy (FR18, NFR4)
        """
        try:
            if service == "llama.cpp":
                health = await self.health_checker.check_llama()
            elif service == "qdrant":
                health = await self.health_checker.check_qdrant()
            else:
                return False

            return health["status"] == "active"
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    async def get_status(self) -> dict[str, Any]:
        """Get update system status.

        Returns:
            Dict with current versions and available backups (FR20, NFR14)
        """
        from datetime import datetime

        from src.core.schemas.update import ServiceVersionInfo

        services_status = {}

        for service in ("llama.cpp", "qdrant"):
            version = self.health_checker.get_current_version(service)
            version_info = ServiceVersionInfo(
                current_version=version or "unknown",
                last_updated=datetime.now() if version else None,
            )
            services_status[service.replace(".", "_")] = version_info.dict()

        return {
            "services": services_status,
        }


_update_service: UpdateService | None = None


def create_update_service() -> UpdateService:
    """Create and cache an update service instance."""
    global _update_service
    if _update_service is None:
        _update_service = UpdateService()
    return _update_service
