"""Enhanced health check service with caching and detailed status."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

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
            "llm": await self._check_llm(config),
            "qdrant": await self._check_qdrant(config),
            "timestamp": time.time(),
        }
        return results

    async def _check_llm(self, config: dict) -> dict[str, Any]:
        """Check LLM service health."""
        cached = self._get_cached("llm")
        if cached:
            return cached

        llm_config = config.get("services", {}).get("llama", {})
        llm_url = llm_config.get("base_url", "http://localhost:11434")

        start = time.time()
        try:
            response = httpx.get(f"{llm_url}/api/tags", timeout=TIMEOUT)
            elapsed = time.time() - start
            result = {
                "status": "ok" if response.status_code == 200 else "error",
                "url": llm_url,
                "response_time": round(elapsed, 3),
                "error": (
                    None
                    if response.status_code == 200
                    else f"HTTP {response.status_code}"
                ),
            }
        except httpx.ConnectError:
            result = {
                "status": "error",
                "url": llm_url,
                "response_time": TIMEOUT,
                "error": "Connection refused",
            }
        except Exception as e:
            result = {
                "status": "error",
                "url": llm_url,
                "response_time": TIMEOUT,
                "error": str(e),
            }

        self._set_cached("llm", result)
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

        start = time.time()
        try:
            from qdrant_client import QdrantClient

            client = QdrantClient(host=host, port=port, timeout=TIMEOUT)
            collections = client.get_collections().collections
            elapsed = time.time() - start

            collection_exists = any(c.name == collection for c in collections)
            result = {
                "status": "ok" if collection_exists else "warning",
                "host": f"{host}:{port}",
                "collection": collection,
                "collection_exists": collection_exists,
                "response_time": round(elapsed, 3),
                "error": (
                    None
                    if collection_exists
                    else f"Collection '{collection}' not found"
                ),
            }
        except ImportError:
            result = {
                "status": "error",
                "host": f"{host}:{port}",
                "error": "qdrant_client not installed",
                "response_time": 0,
            }
        except Exception as e:
            result = {
                "status": "error",
                "host": f"{host}:{port}",
                "response_time": time.time() - start,
                "error": str(e),
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
