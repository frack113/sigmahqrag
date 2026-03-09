"""
Notification Component

A component for displaying toast-style notifications to users.
"""

from nicegui import ui
from typing import Literal


def show_notification(
    message: str, 
    type: Literal['positive', 'negative', 'warning', 'info'] = 'info',
    timeout: int = 3000,
    position: Literal['top-right', 'top-left', 'bottom-right', 'bottom-left', 'top', 'bottom'] = 'top-right'
):
    """
    Show a notification toast.
    
    Args:
        message: The notification message
        type: Type of notification ('positive', 'negative', 'warning', 'info')
        timeout: Auto-dismiss timeout in milliseconds (0 = no timeout)
        position: Position of the notification
    """
    ui.notify(
        message=message,
        type=type,
        timeout=timeout,
        position=position
    )


class NotificationManager:
    """
    A manager for handling different types of notifications.
    """
    
    @staticmethod
    def success(message: str, timeout: int = 3000):
        """Show a success notification."""
        show_notification(message, type='positive', timeout=timeout)
    
    @staticmethod
    def error(message: str, timeout: int = 5000):
        """Show an error notification."""
        show_notification(message, type='negative', timeout=timeout)
    
    @staticmethod
    def warning(message: str, timeout: int = 4000):
        """Show a warning notification."""
        show_notification(message, type='warning', timeout=timeout)
    
    @staticmethod
    def info(message: str, timeout: int = 3000):
        """Show an info notification."""
        show_notification(message, type='info', timeout=timeout)