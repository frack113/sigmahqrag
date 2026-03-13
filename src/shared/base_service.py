"""
Base classes for services and components.

Provides common functionality and interfaces for all services and components
in the SigmaHQ RAG application.
"""

import asyncio
import hashlib
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator, Callable
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any


@dataclass
class CacheEntry:
    """Represents a cached value with metadata."""

    value: Any
    timestamp: float
    ttl: int


class BaseService(ABC):
    """Base class for all services with common functionality."""

    def __init__(self, logger_name: str):
        self.logger = logging.getLogger(logger_name)

    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the service."""
        pass

    @abstractmethod
    def cleanup(self) -> None:
        """Clean up resources."""
        pass

    def _log_operation(
        self, operation: str, success: bool, details: dict[str, Any] | None = None
    ) -> None:
        """Standardized operation logging."""
        level = logging.INFO if success else logging.ERROR
        message = f"{operation}: {'SUCCESS' if success else 'FAILED'}"
        if details:
            message += f" - {details}"
        self.logger.log(level, message)

    def _generate_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()


class AsyncComponent:
    """Base class for async Gradio components."""

    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.is_processing = False

    async def run_in_executor(self, func: Callable, *args, **kwargs) -> Any:
        """Run function in thread pool executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args, **kwargs)

    async def safe_llm_call(self, func: Callable, *args, **kwargs) -> Any:
        """Safe wrapper for LLM calls with timeout and retry logic."""
        try:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=300)
        except asyncio.TimeoutError:
            return "Error: LLM response timed out"
        except Exception as e:
            return f"Error: {str(e)}"

    def cleanup(self) -> None:
        """Clean up resources."""
        if hasattr(self, "executor"):
            self.executor.shutdown(wait=True)


class CacheService:
    """Centralized caching service with LRU eviction."""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: dict[str, CacheEntry] = {}
        self._access_times: dict[str, float] = {}
        self._lock = asyncio.Lock()

    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = str(args) + str(sorted(kwargs.items()))
        return hashlib.md5(key_data.encode()).hexdigest()

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            current_time = time.time()

            if current_time - entry.timestamp > entry.ttl:
                del self._cache[key]
                del self._access_times[key]
                return None

            self._access_times[key] = current_time
            return entry.value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Set value in cache."""
        async with self._lock:
            if len(self._cache) >= self.max_size:
                self._evict_lru()

            entry = CacheEntry(
                value=value, timestamp=time.time(), ttl=ttl or self.default_ttl
            )
            self._cache[key] = entry
            self._access_times[key] = time.time()

    def _evict_lru(self) -> None:
        """Evict least recently used entry."""
        if not self._access_times:
            return

        lru_key = min(self._access_times.items(), key=lambda x: x[1])[0]
        del self._cache[lru_key]
        del self._access_times[lru_key]

    async def clear(self) -> None:
        """Clear all cache entries."""
        async with self._lock:
            self._cache.clear()
            self._access_times.clear()

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        valid_entries = sum(
            1
            for _, timestamp in self._cache.items()
            if current_time - timestamp.timestamp <= timestamp.ttl
        )

        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
            "cache_size_limit": self.max_size,
            "cache_ttl": self.default_ttl,
        }


class AsyncResourceManager:
    """Async resource manager for proper cleanup."""

    def __init__(self):
        self._resources = []

    async def add_resource(self, resource: Any) -> None:
        """Add resource to cleanup list."""
        self._resources.append(resource)

    async def cleanup(self) -> None:
        """Clean up all resources."""
        for resource in self._resources:
            if hasattr(resource, "cleanup"):
                await resource.cleanup()
            elif hasattr(resource, "close"):
                resource.close()
        self._resources.clear()


@asynccontextmanager
async def async_resource_manager() -> AsyncGenerator[AsyncResourceManager, None]:
    """Async context manager for resource management."""
    manager = AsyncResourceManager()
    try:
        yield manager
    finally:
        await manager.cleanup()
