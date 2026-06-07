"""Health check for llama.cpp service."""

from __future__ import annotations

from src.shared.health import check_service_health as _check

DEFAULT_PORT = 8080


async def check_health(timeout: float = 2.0, port: int = DEFAULT_PORT) -> dict:
    """Check health of llama.cpp service."""
    return await _check(component="llama.cpp", port=port, timeout=timeout)
