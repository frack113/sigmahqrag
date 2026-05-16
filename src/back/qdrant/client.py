"""Shared QdrantClient factory."""

from __future__ import annotations

from typing import Any

import qdrant_client

_client_instance: qdrant_client.QdrantClient | None = None


def get_qdrant_client(
    host: str | None = None,
    port: int | None = None,
    timeout: float | None = None,
) -> qdrant_client.QdrantClient:
    """Get (or create) a QdrantClient.

    Returns a shared singleton when using defaults (no custom host/port/timeout).
    Creates a new client when custom parameters are provided.

    Args:
        host: Defaults to config.qdrant_host.
        port: Defaults to config.qdrant_port.
        timeout: Optional custom timeout (prevents caching).

    Returns:
        Configured QdrantClient.
    """
    global _client_instance
    from src.shared import get_config

    cfg = get_config()
    resolved_host = host or cfg.qdrant_host
    resolved_port = port or cfg.qdrant_port

    if host is not None or port is not None or timeout is not None:
        kwargs: dict[str, Any] = {"host": resolved_host, "port": resolved_port}
        if timeout is not None:
            kwargs["timeout"] = timeout
        return qdrant_client.QdrantClient(**kwargs)

    if _client_instance is not None:
        return _client_instance
    _client_instance = qdrant_client.QdrantClient(
        host=resolved_host, port=resolved_port
    )
    return _client_instance
