"""Enhanced health check service with caching and detailed status."""

from __future__ import annotations

import logging
import time
from typing import Any

from src.config import load_config

logger = logging.getLogger(__name__)

CACHE_TTL = 10  # seconds
TIMEOUT = 5.0


class HealthCheckService:
    """Service for system health monitoring."""

    def __init__(self) -> None:
        self._cache: dict[str, dict[str, Any]] = {}
        self._cache_timestamps: dict[str, float] = {}

    async def check_all(self) -> dict[str, Any]:
        """Check all system components.

        Returns:
            Dict with status for each component
        """
        config = load_config()
        results = {
            "llamacpp": await self._check_llamacpp(config),
            "qdrant": await self._check_qdrant(config),
            "timestamp": time.time(),
        }
        return results

    async def _check_llamacpp(self, config: dict) -> dict[str, Any]:
        """Check llama.cpp service health."""
        cached = self._get_cached("llamacpp")
        if cached:
            return cached

        from src.core.backend.llamacpp.health import check_health

        start = time.time()
        result = await check_health(port=8080)
        result["response_time"] = round(time.time() - start, 3)
        self._set_cached("llamacpp", result)
        return result

    async def _check_qdrant(self, config: dict) -> dict[str, Any]:
        """Check Qdrant health."""
        cached = self._get_cached("qdrant")
        if cached:
            return cached

        qdrant_config = config.get("services", {}).get("qdrant", {})
        host = qdrant_config.get("host", "localhost")
        port = qdrant_config.get("port", 6333)
        collection = qdrant_config.get("collection_name", "sigma_rules")

        from src.core.backend.qdrant.health import check_health

        basic_check = await check_health(port=port)
        start = time.time()

        if basic_check["status"] == "active":
            try:
                from qdrant_client import QdrantClient

                client = QdrantClient(host=host, port=port, timeout=TIMEOUT)
                collections = client.get_collections().collections
                collection_exists = any(c.name == collection for c in collections)
                result = {
                    "status": "ok" if collection_exists else "warning",
                    "host": f"{host}:{port}",
                    "collection": collection,
                    "collection_exists": collection_exists,
                    "response_time": round(time.time() - start, 3),
                }
            except Exception as e:
                result = {
                    "status": "warning",
                    "host": f"{host}:{port}",
                    "response_time": round(time.time() - start, 3),
                    "error": str(e),
                }
        else:
            result = {
                "status": "error",
                "host": f"{host}:{port}",
                "collection": collection,
                "response_time": round(time.time() - start, 3),
                "error": basic_check.get("message", "Service unavailable"),
            }

        self._set_cached("qdrant", result)
        return result

    def _get_cached(self, key: str) -> dict[str, Any] | None:
        """Get cached result if not expired."""
        if key not in self._cache:
            return None
        if time.time() - self._cache_timestamps.get(key, 0) > CACHE_TTL:
            del self._cache[key]
            return None
        return self._cache[key]

    def _set_cached(self, key: str, value: dict[str, Any]) -> None:
        """Cache a result."""
        self._cache[key] = value
        self._cache_timestamps[key] = time.time()
