"""Health check for Qdrant service."""

from __future__ import annotations

from src.shared.health import check_service_health as _check

DEFAULT_PORT = 6333


async def check_health(timeout: float = 2.0, port: int = DEFAULT_PORT) -> dict:
    """Check health of Qdrant service."""
    return await _check(component="qdrant", port=port, path="/healthz", timeout=timeout)
