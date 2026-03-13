"""
Utility functions for SigmaHQ RAG application.

Provides common utility functions used across the application.
"""

import asyncio
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
from typing import (
    Any,
)


def handle_service_errors(
    error_types: list[type[Exception]] | None = None,
    default_message: str = "Service operation failed"
) -> Callable:
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
                
                # Check if this is an expected error type
                if error_types and any(isinstance(e, error_type) for error_type in error_types):
                    raise
                
                # Log the error with full traceback
                logger.error(
                    f"Service error in {func.__name__}: {e}\n"
                    f"Traceback: {traceback.format_exc()}"
                )
                
                # Re-raise as ServiceError for consistency
                from .exceptions import ServiceError
                raise ServiceError(f"{default_message}: {str(e)}")
        return wrapper
    return decorator


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exceptions: tuple[type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator for retrying operations with exponential backoff.
    
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
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_retries:
                        break
                    
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    
                    logger = logging.getLogger(func.__module__)
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    await asyncio.sleep(delay)
            
            # If we get here, all retries failed
            raise last_exception
        
        return wrapper
    return decorator


def rate_limit(max_calls: int, time_window: float):
    """
    Decorator for rate limiting function calls.
    
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
        async def wrapper(*args, **kwargs):
            with lock:
                now = time.time()
                
                # Remove old calls outside the time window
                calls[:] = [call_time for call_time in calls if now - call_time < time_window]
                
                # Check if we're within the rate limit
                if len(calls) >= max_calls:
                    raise Exception(f"Rate limit exceeded: {max_calls} calls per {time_window} seconds")
                
                # Add current call
                calls.append(now)
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def async_to_sync(async_func: Callable) -> Callable:
    """
    Convert an async function to sync by running it in an event loop.
    
    Args:
        async_func: Async function to convert
    
    Returns:
        Sync version of the function
    """
    @wraps(async_func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # No event loop running, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        if loop.is_running():
            # Event loop is already running, use create_task
            return loop.create_task(async_func(*args, **kwargs))
        else:
            # Run the async function
            return loop.run_until_complete(async_func(*args, **kwargs))
    
    return wrapper


def sync_to_async(sync_func: Callable) -> Callable:
    """
    Convert a sync function to async by running it in a thread pool.
    
    Args:
        sync_func: Sync function to convert
    
    Returns:
        Async version of the function
    """
    @wraps(sync_func)
    async def wrapper(*args, **kwargs):
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_func, *args, **kwargs)
    
    return wrapper


@contextmanager
def timer(operation_name: str):
    """
    Context manager for timing operations.
    
    Args:
        operation_name: Name of the operation being timed
    
    Yields:
        None
    """
    start_time = time.time()
    try:
        yield
    finally:
        end_time = time.time()
        duration = end_time - start_time
        logger = logging.getLogger(__name__)
        logger.info(f"{operation_name} completed in {duration:.4f} seconds")


@asynccontextmanager
async def async_timer(operation_name: str):
    """
    Async context manager for timing operations.
    
    Args:
        operation_name: Name of the operation being timed
    
    Yields:
        None
    """
    start_time = time.time()
    try:
        yield
    finally:
        end_time = time.time()
        duration = end_time - start_time
        logger = logging.getLogger(__name__)
        logger.info(f"{operation_name} completed in {duration:.4f} seconds")


def generate_hash(data: str | bytes | dict | list) -> str:
    """
    Generate a hash for the given data.
    
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


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal and other security issues.
    
    Args:
        filename: Original filename
    
    Returns:
        Sanitized filename
    """
    # Remove dangerous characters
    safe_chars = re.sub(r'[^\w\s.-]', '', filename)
    
    # Remove leading dots and slashes
    safe_chars = safe_chars.lstrip('.').lstrip('/')
    
    # Limit length
    if len(safe_chars) > 255:
        name, ext = os.path.splitext(safe_chars)
        safe_chars = name[:255-len(ext)] + ext
    
    return safe_chars


def validate_file_upload(
    file_path: str,
    allowed_extensions: list[str] | None = None,
    max_size_mb: int = 10
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
    import os
    
    if not os.path.exists(file_path):
        return False
    
    # Check file size
    file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if file_size_mb > max_size_mb:
        return False
    
    # Check file extension
    if allowed_extensions:
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in allowed_extensions:
            return False
    
    return True


def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 200) -> list[str]:
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

        # Move start position with overlap
        start = end - chunk_overlap

    return chunks


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
    import os
    
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
        logger = logging.getLogger(__name__)
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
    try:
        for key in keys:
            data = data[key]
        return data
    except (KeyError, TypeError):
        return default


def set_nested_value(data: dict, keys: list[str], value: Any) -> None:
    """
    Set nested value in dictionary using list of keys.
    
    Args:
        data: Dictionary to modify
        keys: List of keys to traverse
        value: Value to set
    """
    for key in keys[:-1]:
        if key not in data:
            data[key] = {}
        data = data[key]
    data[keys[-1]] = value


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


def flatten_dict(d: dict, parent_key: str = '', sep: str = '.') -> dict:
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


def is_valid_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
    
    Returns:
        True if email is valid
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def is_valid_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
    
    Returns:
        True if URL is valid
    """
    pattern = r'^https?://[^\s/$.?#].[^\s]*$'
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
    return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))


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
    
    bar = '█' * filled_width + ' ' * (width - filled_width)
    return f"[{bar}] {current}/{total} ({percentage:.1f}%)"


async def batch_process(
    items: list[Any],
    process_func: Callable,
    batch_size: int = 10,
    delay: float = 0.1
) -> list[Any]:
    """
    Process items in batches with optional delay.
    
    Args:
        items: List of items to process
        process_func: Function to process each item
        batch_size: Number of items to process in each batch
        delay: Delay between batches in seconds
    
    Returns:
        List of processed results
    """
    results = []
    
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        batch_results = await asyncio.gather(*[process_func(item) for item in batch])
        results.extend(batch_results)
        
        if delay > 0 and i + batch_size < len(items):
            await asyncio.sleep(delay)
    
    return results


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
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to delete {file_path}: {e}")
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error cleaning up temp files: {e}")
    
    return deleted_count