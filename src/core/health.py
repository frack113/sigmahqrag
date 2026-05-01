"""Health check module (Story 3.3 - GREEN phase)."""

from __future__ import annotations

from typing import Any

import httpx


async def check_llama_cpp(timeout: float = 2.0) -> dict[str, Any]:
    """Check health of llama.cpp service on port 8080 (FR18, NFR4, NFR14)."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:8080/health", timeout=timeout
            )
        if response.status_code == 200:
            return {"status": "active", "component": "llama.cpp", "port": 8080}
        return {
            "status": "inactive",
            "component": "llama.cpp",
            "port": 8080,
            "message": f"HTTP {response.status_code}",
        }
    except (httpx.ConnectError, httpx.ConnectTimeout, TimeoutError):
        return {
            "status": "inactive",
            "component": "llama.cpp",
            "port": 8080,
            "message": "Connection refused or timeout",
        }
    except Exception as e:
        return {
            "status": "inactive",
            "component": "llama.cpp",
            "port": 8080,
            "message": str(e),
        }


async def check_qdrant(timeout: float = 2.0) -> dict[str, Any]:
    """Check health of Qdrant service on port 6333 (FR18, NFR4, NFR14)."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "http://localhost:6333/health", timeout=timeout
            )
        if response.status_code == 200:
            return {"status": "active", "component": "qdrant", "port": 6333}
        return {
            "status": "inactive",
            "component": "qdrant",
            "port": 6333,
            "message": f"HTTP {response.status_code}",
        }
    except (httpx.ConnectError, httpx.ConnectTimeout, TimeoutError):
        return {
            "status": "inactive",
            "component": "qdrant",
            "port": 6333,
            "message": "Connection refused or timeout",
        }
    except Exception as e:
        return {
            "status": "inactive",
            "component": "qdrant",
            "port": 6333,
            "message": str(e),
        }


async def check_all() -> dict[str, Any]:
    """Check health of all services (FR18, NFR4).

    Returns combined health status for all components.
    """
    llama_health = await check_llama_cpp()
    qdrant_health = await check_qdrant()

    return {
        "llama_cpp": llama_health,
        "qdrant": qdrant_health,
    }
