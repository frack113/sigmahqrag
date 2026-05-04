"""Health check module (Story 3.3 - GREEN phase)."""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from src.core.backend.llamacpp.health import check_health as check_llamacpp_health
from src.core.backend.qdrant.health import check_health as check_qdrant_health

MAX_TOTAL_TIMEOUT = 5.0


async def check_llama_cpp(timeout: float = 2.0) -> dict[str, Any]:
    """Check health of llama.cpp service on port 8080."""
    return await check_llamacpp_health(timeout=timeout, port=8080)


async def check_qdrant(timeout: float = 2.0) -> dict[str, Any]:
    """Check health of Qdrant service on port 6333."""
    return await check_qdrant_health(timeout=timeout, port=6333)


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
