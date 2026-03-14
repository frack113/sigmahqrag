"""
Base classes for services and components.

Provides common functionality for all services in SigmaHQ RAG.
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """Base class for all services."""

    def __init__(self):
        pass

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
        logger.log(level, message)

    def update_response_time(self, response_time: float) -> None:
        """Update average response time."""
        pass

    def update_request_count(
        self, success: bool = True, error: str | None = None
    ) -> None:
        """Update request counters."""
        pass

    def update_memory_usage(self, memory_mb: float) -> None:
        """Update memory usage."""
        pass

    def update_cpu_usage(self, cpu_percent: float) -> None:
        """Update CPU usage."""
        pass


class CacheService:
    """Simple caching service."""

    def __init__(self):
        self._cache: dict[str, Any] = {}

    def get(self, key: str) -> Any | None:
        """Get value from cache."""
        return self._cache.get(key)

    def set(self, key: str, value: Any) -> None:
        """Set value in cache."""
        self._cache[key] = value

    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics."""
        return {"total_entries": len(self._cache)}
