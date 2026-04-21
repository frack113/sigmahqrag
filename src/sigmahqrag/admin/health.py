"""Service health checking utilities."""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass
from enum import StrEnum

import httpx

logger = logging.getLogger(__name__)


def _is_cache_valid(cached: tuple[ServiceHealth, float], ttl: float) -> bool:
    """Check if cache entry is valid.

    Args:
        cached: Tuple of (health, timestamp)
        ttl: TTL in seconds

    Returns:
        True if cache is valid
    """
    import time
    return (time.time() - cached[1]) < ttl


class ServiceStatus(StrEnum):
    """Service status values."""

    RUNNING = "running"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ServiceHealth:
    """Health status for a service."""

    name: str
    status: ServiceStatus
    port: int
    url: str
    message: str = ""


LLAMA_DEFAULT_PORT = 8080
QDRANT_DEFAULT_PORT = 6333
LLAMA_HEALTH_ENDPOINT = "/v1/models"
QDRANT_HEALTH_ENDPOINT = "/health"


class HealthChecker:
    """Check health of services."""

    def __init__(
        self,
        llama_port: int = LLAMA_DEFAULT_PORT,
        qdrant_port: int = QDRANT_DEFAULT_PORT,
        cache_ttl: float = 30.0,
    ) -> None:
        """Initialize health checker.

        Args:
            llama_port: Port for llama.cpp server
            qdrant_port: Port for Qdrant server
            cache_ttl: Cache TTL in seconds
        """
        self.llama_port = llama_port
        self.qdrant_port = qdrant_port
        self.timeout = 5.0
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[ServiceHealth, float]] = {}

    async def check_llama(self) -> ServiceHealth:
        """Check llama.cpp service health.

        Returns:
            ServiceHealth for llama.cpp
        """
        import time

        if "llama" in self._cache:
            cached, ts = self._cache["llama"]
            if _is_cache_valid((cached, ts), self.cache_ttl):
                return cached

        url = f"http://localhost:{self.llama_port}{LLAMA_HEALTH_ENDPOINT}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    health = ServiceHealth(
                        name="llama.cpp",
                        status=ServiceStatus.RUNNING,
                        port=self.llama_port,
                        url=url,
                    )
                else:
                    health = ServiceHealth(
                        name="llama.cpp",
                        status=ServiceStatus.UNKNOWN,
                        port=self.llama_port,
                        url=url,
                        message=f"HTTP {response.status_code}",
                    )

        except httpx.ConnectError:
            health = ServiceHealth(
                name="llama.cpp",
                status=ServiceStatus.STOPPED,
                port=self.llama_port,
                url=url,
                message="Connection refused",
            )
        except Exception as e:
            logger.error(f"Health check failed for llama.cpp: {e}")
            health = ServiceHealth(
                name="llama.cpp",
                status=ServiceStatus.UNKNOWN,
                port=self.llama_port,
                url=url,
                message=str(e),
            )

        self._cache["llama"] = (health, time.time())
        return health

    async def check_qdrant(self) -> ServiceHealth:
        """Check Qdrant service health.

        Returns:
            ServiceHealth for Qdrant
        """
        import time

        if "qdrant" in self._cache:
            cached, ts = self._cache["qdrant"]
            if _is_cache_valid((cached, ts), self.cache_ttl):
                return cached

        url = f"http://localhost:{self.qdrant_port}{QDRANT_HEALTH_ENDPOINT}"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)

                if response.status_code == 200:
                    health = ServiceHealth(
                        name="qdrant",
                        status=ServiceStatus.RUNNING,
                        port=self.qdrant_port,
                        url=url,
                    )
                else:
                    health = ServiceHealth(
                        name="qdrant",
                        status=ServiceStatus.UNKNOWN,
                        port=self.qdrant_port,
                        url=url,
                        message=f"HTTP {response.status_code}",
                    )

        except httpx.ConnectError:
            health = ServiceHealth(
                name="qdrant",
                status=ServiceStatus.STOPPED,
                port=self.qdrant_port,
                url=url,
                message="Connection refused",
            )
        except Exception as e:
            logger.error(f"Health check failed for qdrant: {e}")
            health = ServiceHealth(
                name="qdrant",
                status=ServiceStatus.UNKNOWN,
                port=self.qdrant_port,
                url=url,
                message=str(e),
            )

        self._cache["qdrant"] = (health, time.time())
        return health

    async def check_all(self) -> dict[str, ServiceHealth]:
        """Check health of all services.

        Returns:
            Dict mapping service name to health status
        """
        self._cache.clear()
        llama_health = await self.check_llama()
        qdrant_health = await self.check_qdrant()

        return {
            "llama": llama_health,
            "qdrant": qdrant_health,
        }

    def clear_cache(self) -> None:
        """Clear health check cache."""
        self._cache.clear()

    def is_port_open(self, host: str, port: int) -> bool:
        """Check if a port is open.

        Args:
            host: Host to check
            port: Port to check

        Returns:
            True if port is open
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        try:
            result = sock.connect_ex((host, port))
            return result == 0
        except OSError:
            return False
        finally:
            sock.close()


def create_health_checker(
    llama_port: int = LLAMA_DEFAULT_PORT,
    qdrant_port: int = QDRANT_DEFAULT_PORT,
) -> HealthChecker:
    """Create a health checker.

    Args:
        llama_port: Port for llama.cpp
        qdrant_port: Port for Qdrant

    Returns:
        HealthChecker instance
    """
    return HealthChecker(llama_port, qdrant_port)
