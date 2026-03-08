# Notification component for NiceGUI
from typing import Literal

from nicegui import ui


def notify(
    message: str, type: Literal["info", "warning", "positive", "negative"] = "info"
):
    """
    Display a notification with the given message and type.

    Args:
        message (str): Message to display.
        type (str): Notification type (info, warning, positive, negative).
    """
    ui.notify(message, type=type)
