"""Generic HTTP health check for services."""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 2.0


async def check_service_health(
    component: str,
    host: str = "localhost",
    port: int = 80,
    path: str = "/health",
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Check health of an HTTP-based service.

    Args:
        component: Service name (e.g. "qdrant", "llama.cpp")
        host: Host address
        port: Port number
        path: Health endpoint path
        timeout: Request timeout in seconds

    Returns:
        Health status dict
    """
    url = f"http://{host}:{port}{path}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout)
        if response.status_code == 200:
            return {"status": "active", "component": component, "port": port}
        return {
            "status": "inactive",
            "component": component,
            "port": port,
            "message": f"HTTP {response.status_code}",
        }
    except httpx.TimeoutException:
        return {
            "status": "inactive",
            "component": component,
            "port": port,
            "message": "timeout",
        }
    except httpx.ConnectError:
        return {
            "status": "inactive",
            "component": component,
            "port": port,
            "message": "Connection refused",
        }
    except httpx.HTTPError as e:
        return {
            "status": "inactive",
            "component": component,
            "port": port,
            "message": f"HTTP error: {e}",
        }
