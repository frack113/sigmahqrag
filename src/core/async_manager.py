"""
Async Operation Manager for SigmaHQ RAG application.

Provides centralized async operation handling with consistent patterns,
timeout management, error handling, and resource cleanup.
"""

import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from ..shared.exceptions import ServiceError


class AsyncOperationManager:
    """
    Central async operation handler with consistent patterns.
    
    Provides:
    - Consistent timeout management
    - Proper error handling with fallback mechanisms
    - Resource cleanup guarantees
    - Async/sync operation unification
    """
    
    def __init__(self, default_timeout: float = 25.0, max_workers: int = 3):
        """
        Initialize the async operation manager.
        
        Args:
            default_timeout: Default timeout for operations in seconds
            max_workers: Maximum number of worker threads
        """
        self.logger = logging.getLogger(__name__)
        self.default_timeout = default_timeout
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = threading.Lock()
        self._is_closed = False
    
    async def execute_with_timeout(
        self, 
        func: Callable, 
        *args, 
        timeout: float | None = None,
        fallback_func: Callable | None = None
    ) -> Any:
        """
        Execute function with timeout and fallback mechanism.
        
        Args:
            func: Function to execute
            *args: Arguments for the function
            timeout: Timeout in seconds (uses default if None)
            fallback_func: Fallback function to call on timeout/error
            
        Returns:
            Result of function execution or fallback
        """
        if self._is_closed:
            raise ServiceError("Async manager is closed")
        
        timeout = timeout or self.default_timeout
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(
                self.run_in_executor(func, *args),
                timeout=timeout
            )
            return result
            
        except asyncio.TimeoutError:
            self.logger.warning(f"Operation timed out after {timeout}s: {func.__name__}")
            return self._get_fallback_result(fallback_func, func, *args)
            
        except Exception as e:
            self.logger.error(f"Async operation failed: {func.__name__} - {e}")
            return self._get_fallback_result(fallback_func, func, *args)
    
    async def run_in_executor(self, func: Callable, *args) -> Any:
        """
        Run sync function in executor with proper error handling.
        
        Args:
            func: Function to execute
            *args: Arguments for the function
            
        Returns:
            Result of function execution
            
        Raises:
            ServiceError: If executor operation fails
        """
        if self._is_closed:
            raise ServiceError("Async manager is closed")
        
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(self.executor, func, *args)
        except Exception as e:
            self.logger.error(f"Executor error in {func.__name__}: {e}")
            raise ServiceError(f"Executor operation failed: {e}")
    
    async def execute_batch(
        self, 
        operations: list[tuple[Callable, tuple]], 
        timeout: float | None = None,
        return_exceptions: bool = True
    ) -> list[Any]:
        """
        Execute multiple operations concurrently with timeout.
        
        Args:
            operations: List of (function, args) tuples
            timeout: Timeout for individual operations
            return_exceptions: Whether to return exceptions or raise them
            
        Returns:
            List of results or exceptions
        """
        timeout = timeout or self.default_timeout
        
        tasks = []
        for func, args in operations:
            task = self.execute_with_timeout(func, *args, timeout=timeout)
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=return_exceptions)
    
    async def execute_sequential(
        self, 
        operations: list[tuple[Callable, tuple]], 
        timeout: float | None = None,
        delay: float = 0.1
    ) -> list[Any]:
        """
        Execute operations sequentially with optional delay.
        
        Args:
            operations: List of (function, args) tuples
            timeout: Timeout for individual operations
            delay: Delay between operations in seconds
            
        Returns:
            List of results
        """
        timeout = timeout or self.default_timeout
        results = []
        
        for i, (func, args) in enumerate(operations):
            result = await self.execute_with_timeout(func, *args, timeout=timeout)
            results.append(result)
            
            # Add delay between operations (except for the last one)
            if delay > 0 and i < len(operations) - 1:
                await asyncio.sleep(delay)
        
        return results
    
    def _get_fallback_result(
        self, 
        fallback_func: Callable | None, 
        original_func: Callable, 
        *args
    ) -> Any:
        """
        Get fallback result for failed operations.
        
        Args:
            fallback_func: Fallback function to try
            original_func: Original function that failed
            *args: Arguments for the functions
            
        Returns:
            Fallback result or error message
        """
        if fallback_func:
            try:
                if asyncio.iscoroutinefunction(fallback_func):
                    # If fallback is async, we need to run it in current event loop
                    # This is tricky, so we'll run it sync for now
                    return self._sync_fallback(fallback_func, *args)
                else:
                    return fallback_func(*args)
            except Exception as e:
                self.logger.error(f"Fallback function failed: {e}")
        
        # Return generic error message
        return f"Error: Operation {original_func.__name__} failed and no fallback available"
    
    def _sync_fallback(self, async_func: Callable, *args) -> Any:
        """
        Run async fallback function synchronously.
        
        Args:
            async_func: Async function to run
            *args: Arguments for the function
            
        Returns:
            Result of function execution
        """
        try:
            # Try to get current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we can't run another coroutine
                # Return a default value instead
                return f"Error: Cannot run async fallback in running event loop"
            else:
                # If loop is not running, we can run the coroutine
                return loop.run_until_complete(async_func(*args))
        except RuntimeError:
            # No event loop available
            return f"Error: No event loop available for async fallback"
    
    def cleanup(self) -> None:
        """Clean up resources and shutdown executor."""
        with self._lock:
            if not self._is_closed:
                try:
                    self.executor.shutdown(wait=True)
                    self._is_closed = True
                    self.logger.info("Async operation manager cleaned up successfully")
                except Exception as e:
                    self.logger.error(f"Error during async manager cleanup: {e}")
    
    def is_closed(self) -> bool:
        """Check if the manager is closed."""
        return self._is_closed
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.cleanup()


class AsyncResourceManager:
    """
    Resource manager for async operations with automatic cleanup.
    """
    
    def __init__(self):
        self._resources = []
        self._lock = threading.Lock()
    
    def add_resource(self, resource: Any) -> None:
        """Add resource to cleanup list."""
        with self._lock:
            self._resources.append(resource)
    
    async def cleanup(self) -> None:
        """Clean up all resources."""
        with self._lock:
            for resource in self._resources:
                try:
                    if hasattr(resource, 'cleanup'):
                        if asyncio.iscoroutinefunction(resource.cleanup):
                            await resource.cleanup()
                        else:
                            resource.cleanup()
                    elif hasattr(resource, 'close'):
                        resource.close()
                except Exception as e:
                    self.logger.error(f"Error cleaning up resource: {e}")
            self._resources.clear()
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()


# Global async manager instance for convenience
_global_async_manager = None
_global_manager_lock = threading.Lock()


def get_async_manager() -> AsyncOperationManager:
    """
    Get the global async manager instance.
    
    Returns:
        Global async manager instance
    """
    global _global_async_manager
    
    with _global_manager_lock:
        if _global_async_manager is None:
            _global_async_manager = AsyncOperationManager()
        
        return _global_async_manager


def cleanup_global_manager() -> None:
    """
    Clean up the global async manager.
    """
    global _global_async_manager
    
    with _global_manager_lock:
        if _global_async_manager:
            _global_async_manager.cleanup()
            _global_async_manager = None


# Register cleanup on exit
import atexit
atexit.register(cleanup_global_manager)