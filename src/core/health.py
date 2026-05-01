"""Health check module (Story 3.3 - GREEN phase)."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

# TODO Growth: Make configurable via environment or config file
LLAMA_URL = "http://localhost:8080/health"
QDRANT_URL = "http://localhost:6333/health"
MAX_TOTAL_TIMEOUT = 5.0  # AC4: all checks within 5s


async def check_llama_cpp(timeout: float = 2.0) -> dict[str, Any]:
    """Check health of llama.cpp service on port 8080 (FR18, NFR4, NFR14)."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(LLAMA_URL, timeout=timeout)
        if response.status_code == 200:
            return {"status": "active", "component": "llama.cpp", "port": 8080}
        return {
            "status": "inactive",
            "component": "llama.cpp",
            "port": 8080,
            "message": f"HTTP {response.status_code}",
        }
    except httpx.TimeoutException:
        return {
            "status": "inactive",
            "component": "llama.cpp",
            "port": 8080,
            "message": "timeout",
        }
    except httpx.ConnectError:
        return {
            "status": "inactive",
            "component": "llama.cpp",
            "port": 8080,
            "message": "Connection refused",
        }
    except httpx.HTTPError:
        return {
            "status": "inactive",
            "component": "llama.cpp",
            "port": 8080,
            "message": "HTTP error",
        }


async def check_qdrant(timeout: float = 2.0) -> dict[str, Any]:
    """Check health of Qdrant service on port 6333 (FR18, NFR4, NFR14)."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(QDRANT_URL, timeout=timeout)
        if response.status_code == 200:
            return {"status": "active", "component": "qdrant", "port": 6333}
        return {
            "status": "inactive",
            "component": "qdrant",
            "port": 6333,
            "message": f"HTTP {response.status_code}",
        }
    except httpx.TimeoutException:
        return {
            "status": "inactive",
            "component": "qdrant",
            "port": 6333,
            "message": "timeout",
        }
    except httpx.ConnectError:
        return {
            "status": "inactive",
            "component": "qdrant",
            "port": 6333,
            "message": "Connection refused",
        }
    except httpx.HTTPError:
        return {
            "status": "inactive",
            "component": "qdrant",
            "port": 6333,
            "message": "HTTP error",
        }


async def check_all() -> dict[str, Any]:
    """Check health of all services in parallel (FR18, NFR4).

    Returns combined health status for all components within 5s (AC4).
    """
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
            "llama_cpp": {"status": "inactive", "component": "llama.cpp", "message": "timeout"},
            "qdrant": {"status": "inactive", "component": "qdrant", "message": "timeout"},
        }
    except httpx.HTTPError:
        return {
            "llama_cpp": {"status": "inactive", "component": "llama.cpp", "message": "HTTP error"},
            "qdrant": {"status": "inactive", "component": "qdrant", "message": "HTTP error"},
        }
