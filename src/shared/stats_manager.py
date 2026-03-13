"""
Centralized Statistics Manager for SigmaHQ RAG application.

Provides a unified interface for tracking service metrics across all components.
Eliminates duplicate statistics tracking code in individual services.
"""

import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class ServiceStats:
    """
    Base class for service statistics.

    Provides common metrics tracking with thread-safe operations.
    Subclasses can extend for service-specific metrics.
    """

    # Conversation/Request metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    active_requests: int = 0
    last_error: str | None = None
    error_count_window: int = 0
    error_window_start: float = field(default_factory=time.time)
    error_window_size: int = 100

    # Performance metrics (moving averages)
    _response_times: list[float] = field(default_factory=list)
    average_response_time: float = 0.0
    min_response_time: float = float("inf")
    max_response_time: float = 0.0

    # System metrics
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    startup_time: float = field(default_factory=time.time)

    # Context retrieval (for RAG-specific services)
    total_context_retrievals: int = 0
    successful_retrievals: int = 0
    average_context_retrieval_time: float = 0.0
    total_tokens_processed: int = 0

    _lock: Lock = field(default_factory=Lock)

    def __post_init__(self):
        """Initialize minimum response time."""
        if self.min_response_time == float("inf"):
            self.min_response_time = 0.0

    @property
    def uptime_seconds(self) -> float:
        """Get service uptime in seconds."""
        return time.time() - self.startup_time

    @property
    def error_rate(self) -> float:
        """Calculate recent error rate (last 100 requests)."""
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests

    def record_request_start(self) -> None:
        """Record start of a new request."""
        with self._lock:
            self.active_requests += 1
            self.total_requests += 1

    def record_request_complete(
        self, response_time: float, success: bool = True, context_time: float = 0.0
    ) -> None:
        """Record completed request with timing info."""
        with self._lock:
            self.active_requests = max(0, self.active_requests - 1)

            if not success:
                self.failed_requests += 1
                self.last_error = "Request failed"
                if len(self._response_times) >= self.error_window_size:
                    self._response_times.pop(0)
                else:
                    self._response_times.append(response_time)

                # Update recent errors for error rate calculation
                current_time = time.time()
                if current_time - self.error_window_start > 60.0:  # Sliding 60s window
                    self.error_count_window = 0
                    self.error_window_start = current_time
                self.error_count_window += 1

            else:
                self.successful_requests += 1

            # Update performance metrics (exponential moving average)
            alpha = 0.1
            if success:
                new_avg = (
                    alpha * response_time + (1 - alpha) * self.average_response_time
                )
                self.average_response_time = new_avg

                # Track min/max with more samples
                if len(self._response_times) >= 10:
                    self._response_times.pop(0)
                self._response_times.append(response_time)
                self.min_response_time = min(self.min_response_time, response_time)
                self.max_response_time = max(self.max_response_time, response_time)

            # Update context retrieval stats if provided
            if context_time > 0:
                self.total_context_retrievals += 1
                successful_retrieval_count = (
                    self.successful_requests
                    if success
                    else self.successful_requests - 1
                )
                if successful_retrieval_count > 0:
                    new_context_avg = (
                        alpha * context_time
                        + (1 - alpha) * self.average_context_retrieval_time
                    )
                    self.average_context_retrieval_time = new_context_avg

            # Capture system metrics periodically

    def record_request_failure(self, error: str) -> None:
        """Record a request failure."""
        with self._lock:
            if self.active_requests > 0:
                self.active_requests = max(0, self.active_requests - 1)
            self.failed_requests += 1
            self.last_error = error
            self.error_count_window += 1

    def clear(self) -> None:
        """Reset all statistics."""
        with self._lock:
            self.__init__()

    @classmethod
    def get_health_status(cls, stats: "ServiceStats") -> dict[str, Any]:
        """Generate health status from service stats."""
        return {
            "requests": stats.total_requests,
            "success_rate": (
                (stats.successful_requests / stats.total_requests * 100)
                if stats.total_requests > 0
                else 100.0
            ),
            "avg_response_time_sec": stats.average_response_time,
            "recent_errors": stats.failed_requests,
            "uptime_sec": stats.uptime_seconds,
        }


def _get_thread_metrics() -> dict[str, Any]:
    """Get system metrics for current thread."""
    try:
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "memory_mb": memory_info.rss / 1024 / 1024,
            "cpu_percent": psutil.cpu_percent(interval=0.1),
        }
    except ImportError:
        return {"error": "psutil not available"}


def get_system_metrics() -> dict[str, float]:
    """Get current system metrics."""
    return _get_thread_metrics()


__all__ = [
    "ServiceStats",
    "get_system_metrics",
]
