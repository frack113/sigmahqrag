"""
Shared Statistics Management Module

Provides common statistics tracking and health status checking functionality
for all services in the SigmaHQ RAG application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class BaseStats:
    """Base class for service statistics - to be subclassed by each service."""

    # Request/response tracking
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    total_responses: int = 0  # For services like chat that track conversations

    # Performance metrics
    average_response_time: float = 0.0
    average_context_retrieval_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = float("inf")

    # Error tracking
    last_error: str | None = None
    error_rate: float = 0.0

    # Resource usage (updated externally)
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0

    # Service lifecycle
    uptime_seconds: float = 0.0
    start_time: datetime = field(default_factory=datetime.now)


def get_memory_usage() -> dict[str, Any]:
    """
    Get current memory usage statistics.

    Returns:
        Dictionary with memory usage information
    """
    try:
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent(),
        }
    except ImportError:
        return {"rss_mb": 0, "vms_mb": 0, "percent": 0}


def get_cpu_usage(interval: float = 1.0) -> float:
    """
    Get current CPU usage percentage.

    Args:
        interval: Time interval for measurement in seconds

    Returns:
        CPU usage percentage (0-100)
    """
    try:
        import psutil

        return psutil.cpu_percent(interval=interval)
    except ImportError:
        return 0.0


def update_base_stats(
    stats: BaseStats | None = None, error: str | None = None
) -> BaseStats:
    """
    Update base statistics with current resource usage and error tracking.

    Args:
        stats: Statistics instance to update (will create new if None)
        error: Optional error string to record

    Returns:
        Updated statistics instance
    """
    if stats is None:
        stats = BaseStats()

    # Update memory and CPU usage
    memory_info = get_memory_usage()
    stats.memory_usage_mb = memory_info.get("rss_mb", 0)
    stats.cpu_usage_percent = get_cpu_usage(0.5)  # Faster interval for periodic checks

    # Update uptime
    stats.uptime_seconds = (datetime.now() - stats.start_time).total_seconds()

    # Update error tracking
    if error:
        stats.failed_requests += 1
        stats.last_error = error
        total = stats.successful_requests + stats.failed_requests
        stats.error_rate = stats.failed_requests / total if total > 0 else 0
    else:
        stats.successful_requests += 1

    return stats


def calculate_moving_average(
    new_value: float, previous_avg: float, count: int
) -> float:
    """
    Calculate moving average using the formula:
    new_avg = (previous_avg * (count-1) + new_value) / count

    Args:
        new_value: New value to incorporate
        previous_avg: Previous moving average
        count: Number of values included so far (including this one)

    Returns:
        New moving average
    """
    if count <= 1:
        return new_value
    return (previous_avg * (count - 1) + new_value) / count


def check_service_health(
    stats: BaseStats,
    threshold_response_time: float = 30.0,
    threshold_memory_mb: float = 1024.0,
    threshold_cpu_percent: float = 80.0,
    error_rate_threshold: float = 0.1,
) -> tuple[str, list[str]]:
    """
    Check service health status based on statistics and thresholds.

    Args:
        stats: Service statistics to check
        threshold_response_time: Max average response time in seconds before degraded
        threshold_memory_mb: Max memory usage in MB before degraded
        threshold_cpu_percent: Max CPU usage percentage before degraded
        error_rate_threshold: Error rate (0-1) above which service is degraded

    Returns:
        Tuple of (status, list of issues)
    """
    status = "healthy"
    issues: list[str] = []

    # Check error rate
    if stats.total_requests > 0 or stats.successful_requests > 0:
        total = stats.successful_requests + stats.failed_requests
        actual_error_rate = stats.failed_requests / total if total > 0 else 0
        if actual_error_rate > error_rate_threshold:
            status = "degraded"
            issues.append(f"High error rate: {actual_error_rate:.2%}")

    # Check response time (only if we have averages)
    if stats.average_response_time > threshold_response_time:
        status = "degraded"
        issues.append(f"High response time: {stats.average_response_time:.2f}s")

    # Check memory usage
    if stats.memory_usage_mb > threshold_memory_mb:
        status = "degraded"
        issues.append(f"High memory usage: {stats.memory_usage_mb:.2f}MB")

    # Check CPU usage
    if stats.cpu_usage_percent > threshold_cpu_percent:
        status = "degraded"
        issues.append(f"High CPU usage: {stats.cpu_usage_percent:.1f}%")

    return status, issues


def get_service_status(
    service_name: str,
    status: str,
    issues: list[str],
) -> dict[str, Any]:
    """
    Build a standardized service status response.

    Args:
        service_name: Name of the service
        status: Health status (healthy/unhealthy/degraded)
        issues: List of issues causing degradation

    Returns:
        Dictionary with service status information
    """
    return {
        "service": service_name,
        "status": status,
        "issues": issues,
        "timestamp": datetime.now().isoformat(),
    }


class ServiceHealthCheck:
    """Protocol for services to implement health checks."""

    def get_health_status(self) -> dict[str, Any]:
        """Get comprehensive health status for the service."""
        ...


def format_stats_for_display(stats: BaseStats) -> dict[str, Any]:
    """
    Format statistics for display in UI.

    Args:
        stats: Statistics to format

    Returns:
        Formatted statistics dictionary
    """
    return {
        "total_requests": stats.total_requests,
        "successful_requests": stats.successful_requests,
        "failed_requests": stats.failed_requests,
        "success_rate": (
            (stats.successful_requests / stats.total_requests * 100)
            if stats.total_requests > 0
            else 100.0
        ),
        "average_response_time": stats.average_response_time,
        "memory_usage_mb": stats.memory_usage_mb,
        "cpu_usage_percent": stats.cpu_usage_percent,
        "uptime_seconds": stats.uptime_seconds,
    }
