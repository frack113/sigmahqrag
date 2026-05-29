"""Enhanced health check service with caching and detailed status."""

from __future__ import annotations

import logging
import time
from typing import Any

from src.shared import get_config

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
        results = {
            "llamacpp": await self._check_llamacpp(),
            "qdrant": await self._check_qdrant(),
            "timestamp": time.time(),
        }
        return results

    async def check_llama(self) -> dict[str, Any]:
        """Check llama.cpp health (public alias)."""
        return await self._check_llamacpp()

    async def check_qdrant(self) -> dict[str, Any]:
        """Check Qdrant health (public alias)."""
        return await self._check_qdrant()

    async def _check_llamacpp(self) -> dict[str, Any]:
        """Check llama.cpp health."""
        cached = self._get_cached("llamacpp")
        if cached:
            return cached

        config = get_config()
        base_url = config.llama_base_url or "http://127.0.0.1:8080"
        import time as time_module

        start = time_module.time()
        status = "error"
        message = ""

        try:
            import httpx

            async with httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT)) as client:
                resp = await client.get(f"{base_url}/health")
                if resp.status_code == 200:
                    status = "active"
                else:
                    message = f"HTTP {resp.status_code}"
        except Exception as e:
            message = str(e)

        result = {
            "status": status,
            "url": base_url,
            "response_time": round(time_module.time() - start, 3),
        }
        if message:
            result["error"] = message

        self._set_cached("llamacpp", result)
        return result

    async def _check_qdrant(self) -> dict[str, Any]:
        """Check Qdrant health."""
        cached = self._get_cached("qdrant")
        if cached:
            return cached

        config = get_config()
        host = config.qdrant_host
        port = config.qdrant_port
        collection = config.qdrant_collection_name

        from src.back.qdrant.health import check_health

        basic_check = await check_health(port=port)
        start = time.time()

        if basic_check["status"] == "active":
            try:
                from src.back.qdrant.client import get_qdrant_client

                client = get_qdrant_client(host=host, port=port, timeout=TIMEOUT)
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

    def get_current_version(self, service: str) -> str | None:
        """Get current version of a service."""
        if service in ("llama", "llama.cpp", "llama_cpp"):
            from src.back.llamacpp import get_version

            return get_version()
        elif service in ("qdrant", "qdrant_db"):
            from src.back.qdrant import get_version

            return get_version()
        return None
