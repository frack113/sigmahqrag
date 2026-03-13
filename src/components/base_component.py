"""
Base Component Pattern for Gradio Components

Provides a common base class for all Gradio components with async support
and shared functionality.
"""

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from src.models.logging_service import get_logger

logger = get_logger(__name__)


class GradioComponent(ABC):
    """
    Base class for all Gradio components.

    Provides common functionality for async operations, error handling,
    and shared services.
    """

    def __init__(self):
        # Shared thread pool executor for background operations
        self.executor = ThreadPoolExecutor(max_workers=2)

        # Component state
        self.is_processing = False

    def cleanup(self):
        """Clean up component resources."""
        try:
            if hasattr(self, "executor"):
                self.executor.shutdown(wait=True)
        except Exception as e:
            logger.error(f"Error during component cleanup: {e}")

    async def run_in_executor(self, func, *args, **kwargs):
        """
        Run a function in the thread pool executor.

        Args:
            func: The function to run
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the function call
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.executor, func, *args, **kwargs)

    async def safe_llm_call(self, func, *args, **kwargs):
        """
        Safe wrapper for LLM calls with timeout and retry logic.

        Args:
            func: The async function to call
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            The result of the function call or an error message
        """
        try:
            # Add timeout protection
            result = await asyncio.wait_for(
                func(*args, **kwargs), timeout=300  # 5 minutes timeout
            )
            return result
        except asyncio.TimeoutError:
            error_msg = "Error: LLM response timed out. Please try again."
            logger.error(error_msg)
            return error_msg
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            logger.error(f"LLM call failed: {e}")
            return error_msg

    def create_status_update(
        self, message: str, is_error: bool = False
    ) -> dict[str, Any]:
        """
        Create a standardized status update message.

        Args:
            message: The status message
            is_error: Whether this is an error message

        Returns:
            Dictionary with status information
        """
        return {
            "message": message,
            "type": "error" if is_error else "info",
            "timestamp": asyncio.get_event_loop().time(),
        }

    @abstractmethod
    def create_tab(self):
        """
        Create and return the Gradio components for this tab.

        This method must be implemented by all subclasses.
        """
        pass


class AsyncComponent(GradioComponent):
    """
    Enhanced base component with additional async utilities.
    """

    async def update_progress(self, progress_callback, message: str, progress: float):
        """
        Update progress for long-running operations.

        Args:
            progress_callback: The callback function to update progress
            message: Progress message
            progress: Progress value (0.0 to 1.0)
        """
        if progress_callback:
            await progress_callback(message, progress)

    async def stream_response(
        self, response_generator: AsyncGenerator[str, None]
    ) -> AsyncGenerator[str, None]:
        """
        Stream response chunks from an async generator.

        Args:
            response_generator: Async generator yielding response chunks

        Yields:
            Response chunks for streaming
        """
        try:
            async for chunk in response_generator:
                yield chunk
        except Exception as e:
            logger.error(f"Error in response streaming: {e}")
            yield f"Error in response streaming: {str(e)}"

    def format_error_message(self, error: Exception, context: str = "") -> str:
        """
        Format an error message with context.

        Args:
            error: The exception
            context: Additional context information

        Returns:
            Formatted error message
        """
        context_msg = f" ({context})" if context else ""
        return f"❌ Error{context_msg}: {str(error)}"
