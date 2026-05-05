"""Health check for Qdrant service."""

from __future__ import annotations

from typing import Any

import httpx

DEFAULT_PORT = 6333
DEFAULT_URL = f"http://localhost:{DEFAULT_PORT}/health"


async def check_health(
    timeout: float = 2.0, port: int = DEFAULT_PORT
) -> dict[str, Any]:
    """Check health of Qdrant service."""
    url = f"http://localhost:{port}/health"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=timeout)
        if response.status_code == 200:
            return {"status": "active", "component": "qdrant", "port": port}
        return {
            "status": "inactive",
            "component": "qdrant",
            "port": port,
            "message": f"HTTP {response.status_code}",
        }
    except httpx.TimeoutException:
        return {
            "status": "inactive",
            "component": "qdrant",
            "port": port,
            "message": "timeout",
        }
    except httpx.ConnectError:
        return {
            "status": "inactive",
            "component": "qdrant",
            "port": port,
            "message": "Connection refused",
        }
    except httpx.HTTPError:
        return {
            "status": "inactive",
            "component": "qdrant",
            "port": port,
            "message": "HTTP error",
        }
