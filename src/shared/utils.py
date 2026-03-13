"""
Utility functions for SigmaHQ RAG application.

Provides common utility functions used across the application.

Note: All async operations use Gradio's native queue=True support,
which handles async execution automatically. Manual event loop management
is not needed and has been removed from utils.py.
"""

import hashlib
import json
import logging
import os
import re
import threading
import time
import traceback
from collections.abc import Callable
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def handle_service_errors(
    error_types: list[type[Exception]] | None = None,
    default_message: str = "Service operation failed",
) -> Callable[[Callable], Callable]:
    """
    Decorator for standardized error handling in services.

    Args:
        error_types: List of specific error types to catch
        default_message: Default error message

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger = logging.getLogger(func.__module__)
                logger.error(
                    f"Service error in {func.__name__}: {e}\n"
                    f"Traceback: {traceback.format_exc()}"
                )
                from .exceptions import ServiceError

                raise ServiceError(f"{default_message}: {str(e)}")

        return wrapper

    return decorator


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable], Callable]:
    """
    Decorator for retrying operations with exponential backoff.

    Note: This decorator is designed for sync functions that run in Gradio's
    event loop. For async functions, use asyncio.sleep directly within the function.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exceptions: Tuple of exception types to catch

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_retries:
                        break

                    delay = min(base_delay * (2**attempt), max_delay)
                    logger = logging.getLogger(func.__module__)
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed "
                        f"for {func.__name__}: {e}. Retrying in {delay:.2f} seconds..."
                    )

                    time.sleep(delay)

            raise last_exception

        return wrapper

    return decorator


def rate_limit(max_calls: int, time_window: float) -> Callable[[Callable], Callable]:
    """
    Decorator for rate limiting function calls.

    Note: For async functions in Gradio, use queue=True instead.

    Args:
        max_calls: Maximum number of calls allowed
        time_window: Time window in seconds

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        calls: list[float] = []
        lock = threading.Lock()

        @wraps(func)
        def wrapper(*args, **kwargs):
            with lock:
                now = time.time()
                calls[:] = [t for t in calls if now - t < time_window]

                if len(calls) >= max_calls:
                    raise Exception(
                        f"Rate limit exceeded: {max_calls} calls per {time_window}s"
                    )

                calls.append(now)

            return func(*args, **kwargs)

        return wrapper

    return decorator


@contextmanager
def timer(operation_name: str):
    """Context manager for timing operations."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"{operation_name} completed in {duration:.4f}s")


@asynccontextmanager
async def async_timer(operation_name: str):
    """Async context manager for timing operations."""
    start_time = time.time()
    try:
        yield
    finally:
        duration = time.time() - start_time
        logger.info(f"{operation_name} completed in {duration:.4f}s")


def generate_hash(data: str | bytes | dict | list) -> str:
    """
    Generate a SHA256 hash for the given data.

    Args:
        data: Data to hash (string, bytes, dict, or list)

    Returns:
        SHA256 hash as hexadecimal string
    """
    if isinstance(data, (dict, list)):
        data = json.dumps(data, sort_keys=True).encode()
    elif isinstance(data, str):
        data = data.encode()
    return hashlib.sha256(data).hexdigest()


def chunk_text(
    text: str, chunk_size: int = 1000, chunk_overlap: int = 200
) -> list[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: Text to chunk
        chunk_size: Size of each chunk in characters
        chunk_overlap: Overlap between chunks in characters

    Returns:
        List of text chunks
    """
    if not text or len(text) == 0:
        return [""]

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end]
        chunks.append(chunk)

        if end == len(text):
            break
        start = end - chunk_overlap

    return chunks


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other security issues.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    safe_chars = re.sub(r"[^\w\s.-]", "", filename)
    safe_chars = safe_chars.lstrip(".").lstrip("/")

    if len(safe_chars) > 255:
        name, ext = os.path.splitext(safe_chars)
        safe_chars = name[: 255 - len(ext)] + ext

    return safe_chars


def validate_file_upload(
    file_path: str,
    allowed_extensions: list[str] | None = None,
    max_size_mb: int = 10,
) -> bool:
    """
    Validate file upload for security.

    Args:
        file_path: Path to the uploaded file
        allowed_extensions: List of allowed file extensions
        max_size_mb: Maximum file size in megabytes

    Returns:
        True if file is valid, False otherwise
    """
    if not os.path.exists(file_path):
        return False

    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        return False

    if allowed_extensions:
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in allowed_extensions:
            return False

    return True


def format_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Human-readable size string
    """
    if size_bytes == 0:
        return "0B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.2f}{size_names[i]}"


def get_file_info(file_path: str) -> dict[str, Any]:
    """
    Get comprehensive file information.

    Args:
        file_path: Path to the file

    Returns:
        Dictionary with file information
    """
    if not os.path.exists(file_path):
        return {"error": "File not found"}

    stat = os.stat(file_path)

    return {
        "filename": os.path.basename(file_path),
        "file_size": stat.st_size,
        "file_size_formatted": format_size(stat.st_size),
        "file_type": os.path.splitext(file_path)[1],
        "created_date": datetime.fromtimestamp(stat.st_ctime),
        "modified_date": datetime.fromtimestamp(stat.st_mtime),
        "accessed_date": datetime.fromtimestamp(stat.st_atime),
        "is_readable": os.access(file_path, os.R_OK),
        "is_writable": os.access(file_path, os.W_OK),
        "is_executable": os.access(file_path, os.X_OK),
    }


def create_directory_if_not_exists(directory_path: str) -> bool:
    """
    Create directory if it doesn't exist.

    Args:
        directory_path: Path to the directory

    Returns:
        True if directory exists or was created successfully
    """
    try:
        Path(directory_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Failed to create directory {directory_path}: {e}")
        return False


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Safely divide two numbers, returning default if division by zero.

    Args:
        numerator: Numerator
        denominator: Denominator
        default: Default value if division by zero

    Returns:
        Division result or default value
    """
    try:
        return numerator / denominator
    except ZeroDivisionError:
        return default


def deep_merge(dict1: dict, dict2: dict) -> dict:
    """
    Deep merge two dictionaries.

    Args:
        dict1: First dictionary
        dict2: Second dictionary

    Returns:
        Merged dictionary
    """
    result = dict1.copy()

    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    """
    Flatten a nested dictionary.

    Args:
        d: Dictionary to flatten
        parent_key: Parent key for nested keys
        sep: Separator for nested keys

    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def get_nested_value(data: dict, keys: list[str], default: Any = None) -> Any:
    """
    Get nested value from dictionary using list of keys.

    Args:
        data: Dictionary to search
        keys: List of keys to traverse
        default: Default value if key not found

    Returns:
        Nested value or default
    """
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def set_nested_value(data: dict, keys: list[str], value: Any) -> bool:
    """
    Set nested value in dictionary using list of keys.

    Args:
        data: Dictionary to modify
        keys: List of keys to traverse
        value: Value to set

    Returns:
        True if successful, False otherwise
    """
    try:
        current = data
        for key in keys[:-1]:
            if isinstance(current, dict) and key not in current:
                current[key] = {}
            elif not isinstance(current, dict):
                return False
            current = current[key]
        if isinstance(current, dict):
            current[keys[-1]] = value
            return True
        return False
    except Exception:
        return False


def is_valid_email(email: str) -> bool:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        True if email is valid
    """
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def is_valid_url(url: str) -> bool:
    """
    Validate URL format.

    Args:
        url: URL to validate

    Returns:
        True if URL is valid
    """
    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    return re.match(pattern, url) is not None


def get_current_timestamp() -> str:
    """
    Get current timestamp in ISO format.

    Returns:
        Current timestamp string
    """
    return datetime.now().isoformat()


def parse_iso_timestamp(timestamp_str: str) -> datetime:
    """
    Parse ISO timestamp string to datetime object.

    Args:
        timestamp_str: ISO timestamp string

    Returns:
        Datetime object
    """
    return datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))


def get_time_ago(timestamp: datetime, now: datetime | None = None) -> str:
    """
    Get human-readable time ago string.

    Args:
        timestamp: Past timestamp
        now: Current timestamp (defaults to now)

    Returns:
        Human-readable time ago string
    """
    if now is None:
        now = datetime.now()

    diff = now - timestamp

    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years != 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months != 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    else:
        return "just now"


def create_progress_bar(current: int, total: int, width: int = 30) -> str:
    """
    Create a text-based progress bar.

    Args:
        current: Current progress
        total: Total progress
        width: Width of the progress bar

    Returns:
        Progress bar string
    """
    if total == 0:
        return "[>                           ] 0/0 (0.0%)"

    percentage = (current / total) * 100
    filled_width = int(width * current // total)
    bar = "█" * filled_width + " " * (width - filled_width)
    return f"[{bar}] {current}/{total} ({percentage:.1f}%)"


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
            "available_mb": psutil.virtual_memory().available / 1024 / 1024,
            "total_mb": psutil.virtual_memory().total / 1024 / 1024,
        }
    except ImportError:
        return {"error": "psutil not available"}


def get_cpu_usage(interval: float = 1.0) -> float:
    """
    Get current CPU usage percentage.

    Args:
        interval: Time interval for measurement

    Returns:
        CPU usage percentage
    """
    try:
        import psutil

        return psutil.cpu_percent(interval=interval)
    except ImportError:
        return 0.0


def get_app_directory() -> Path:
    """
    Get the application directory path.

    Returns:
        Path object representing the application directory
    """
    current_file = Path(__file__)
    app_dir = current_file.parent.parent.parent
    return app_dir


def cleanup_temp_files(directory: str, age_hours: int = 24) -> int:
    """
    Clean up temporary files older than specified age.

    Args:
        directory: Directory to clean
        age_hours: Age threshold in hours

    Returns:
        Number of files deleted
    """
    from pathlib import Path

    deleted_count = 0
    cutoff_time = time.time() - (age_hours * 3600)

    try:
        for file_path in Path(directory).glob("*"):
            if file_path.stat().st_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path}: {e}")
    except Exception as e:
        logger.error(f"Error cleaning up temp files: {e}")

    return deleted_count


def calculate_moving_average(values: list[float], window_size: int = 5) -> list[float]:
    """
    Calculate moving average for a list of values.

    Args:
        values: List of numeric values
        window_size: Size of the moving window

    Returns:
        List of moving average values
    """
    if not values:
        return []

    result = []
    for i in range(len(values)):
        start_idx = max(0, i - window_size + 1)
        window = values[start_idx : i + 1]
        result.append(sum(window) / len(window))

    return result


def truncate_string(text: str, max_length: int, ellipsis: str = "...") -> str:
    """
    Truncate a string to a maximum length with an ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length
        ellipsis: String to append if truncated

    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - len(ellipsis)] + ellipsis


def parse_boolean(value: Any) -> bool | None:
    """
    Parse a value as boolean.

    Args:
        value: Value to parse

    Returns:
        Boolean value or None if parsing fails
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "1", "on")
    if isinstance(value, (int, float)):
        return bool(value)
    return None


def get_file_extension(filename: str) -> str:
    """
    Get the file extension from a filename.

    Args:
        filename: Filename or path

    Returns:
        File extension with dot prefix
    """
    _, ext = os.path.splitext(filename)
    return ext.lower()


def is_file_extension_allowed(filename: str, allowed_extensions: list[str]) -> bool:
    """
    Check if a file extension is in the allowed list.

    Args:
        filename: Filename to check
        allowed_extensions: List of allowed extensions

    Returns:
        True if extension is allowed
    """
    ext = get_file_extension(filename)
    return ext in [e.lower() for e in allowed_extensions]


def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely load JSON from a string.

    Args:
        json_str: JSON string to parse
        default: Default value if parsing fails

    Returns:
        Parsed JSON or default value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        return default


def safe_json_dumps(obj: Any, indent: int = 2) -> str:
    """
    Safely dump object to JSON string.

    Args:
        obj: Object to serialize
        indent: Indentation level

    Returns:
        JSON string or empty string if serialization fails
    """
    try:
        return json.dumps(obj, indent=indent, default=str)
    except (TypeError, ValueError):
        return ""


def get_timezone_name() -> str:
    """Get the current timezone name."""
    import zoneinfo

    return zoneinfo.ZoneInfo(key="local").key
