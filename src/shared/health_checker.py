"""Health check module."""

from __future__ import annotations

import asyncio
from enum import Enum

from src.back.llamacpp.health import check_health as check_llamacpp_health
from src.back.qdrant.health import check_health as check_qdrant_health

MAX_TOTAL_TIMEOUT = 5.0


class ServiceStatus(Enum):
    """Service status enum."""

    RUNNING = "running"
    STOPPED = "stopped"
    UNKNOWN = "unknown"


class ServiceHealth:
    """Service health status."""

    def __init__(
        self,
        status: ServiceStatus,
        message: str = "",
        name: str = "",
        port: int = 0,
        url: str = "",
    ):
        self.status = status
        self.message = message
        self.name = name
        self.port = port
        self.url = url


class HealthChecker:
    """Health checker for services."""

    async def check_all(self) -> dict[str, ServiceHealth]:
        llamacpp = await self.check_llamacpp()
        qdrant = await self.check_qdrant()
        return {
            "llamacpp": llamacpp,
            "qdrant": qdrant,
        }

    async def check_llamacpp(self) -> ServiceHealth:
        result = await check_llamacpp_health(port=8080)
        if result["status"] == "active":
            return ServiceHealth(
                ServiceStatus.RUNNING,
                name="llama.cpp",
                port=8080,
                url="http://localhost:8080",
            )
        return ServiceHealth(
            ServiceStatus.STOPPED,
            result.get("message", ""),
            name="llama.cpp",
            port=8080,
            url="http://localhost:8080",
        )

    async def check_qdrant(self) -> ServiceHealth:
        result = await check_qdrant_health(port=6333)
        if result["status"] == "active":
            return ServiceHealth(
                ServiceStatus.RUNNING,
                name="qdrant",
                port=6333,
                url="http://localhost:6333",
            )
        return ServiceHealth(
            ServiceStatus.STOPPED,
            result.get("message", ""),
            name="qdrant",
            port=6333,
            url="http://localhost:6333",
        )


def create_health_checker() -> HealthChecker:
    """Create a health checker instance."""
    return HealthChecker()


async def check_llama_cpp(timeout: float = 2.0) -> dict:
    """Check health of llama.cpp service on port 8080."""
    return await check_llamacpp_health(timeout=timeout, port=8080)


async def check_qdrant(timeout: float = 2.0) -> dict:
    """Check health of Qdrant service on port 6333."""
    return await check_qdrant_health(timeout=timeout, port=6333)


async def check_all() -> dict:
    """Check health of all services in parallel (FR18, NFR4).

    Returns combined health status for all components within 5s (AC4).
    """
    import httpx

    try:
        results = await asyncio.wait_for(
            asyncio.gather(check_llama_cpp(), check_qdrant()),
            timeout=MAX_TOTAL_TIMEOUT,
        )
        return {
            "llama_cpp": results[0],
            "qdrant": results[1],
        }
    except TimeoutError:
        return {
            "llama_cpp": {
                "status": "inactive",
                "component": "llama.cpp",
                "message": "timeout",
            },
            "qdrant": {
                "status": "inactive",
                "component": "qdrant",
                "message": "timeout",
            },
        }
    except httpx.HTTPError:
        return {
            "llama_cpp": {
                "status": "inactive",
                "component": "llama.cpp",
                "message": "HTTP error",
            },
            "qdrant": {
                "status": "inactive",
                "component": "qdrant",
                "message": "HTTP error",
            },
        }
