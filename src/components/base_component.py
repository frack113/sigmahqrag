"""
Base Component Pattern for Gradio Components.

Provides a common base class for all Gradio components using synchronous methods.
Async operations are handled by Gradio's native queue system.
"""

from abc import ABC, abstractmethod
from typing import Any

from src.models.logging_service import get_logger

logger = get_logger(__name__)


class GradioComponent(ABC):
    """
    Base class for all Gradio components.

    Provides common functionality for:
    - Resource cleanup
    - Error handling utilities
    - Logging
    """

    def __init__(self):
        # Component state
        self.is_processing = False

    def cleanup(self):
        """Clean up component resources."""
        pass

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
        }

    @abstractmethod
    def create_tab(self):
        """
        Create and return the Gradio components for this tab.

        This method must be implemented by all subclasses.
        """
        pass


# All async utilities have been removed.
# Use Gradio's native queue system with concurrency_limit for async operations.


def format_error_message(error: Exception, context: str = "") -> str:
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
