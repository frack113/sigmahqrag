"""
Confirm Dialog Component

Component for displaying confirmation dialogs with custom messages and actions.
"""

from typing import Optional, Callable
from nicegui import ui


class ConfirmDialog:
    """
    A component for displaying confirmation dialogs.

    Attributes:
        title: Dialog title
        message: Dialog message
        confirm_text: Text for confirm button
        cancel_text: Text for cancel button
        on_confirm: Callback function when confirmed
        on_cancel: Callback function when cancelled
    """

    def __init__(
        self,
        title: str = "Confirm",
        message: str = "Are you sure?",
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel",
        on_confirm: Optional[Callable] = None,
        on_cancel: Optional[Callable] = None,
    ):
        """
        Initialize the confirm dialog component.

        Args:
            title: Dialog title
            message: Dialog message
            confirm_text: Text for confirm button
            cancel_text: Text for cancel button
            on_confirm: Callback when confirmed
            on_cancel: Callback when cancelled
        """
        self.title = title
        self.message = message
        self.confirm_text = confirm_text
        self.cancel_text = cancel_text
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        self.dialog = None

    def render(self):
        """
        Render the confirm dialog.

        Returns:
            The dialog element
        """
        # Create dialog
        self.dialog = ui.dialog()

        with self.dialog:
            with ui.card().classes("w-96"):
                # Title
                ui.label(self.title).classes("text-lg font-bold mb-2")

                # Message
                ui.label(self.message).classes("text-sm text-gray-600 mb-4")

                # Buttons
                with ui.row().classes("justify-end gap-2"):
                    ui.button(
                        self.cancel_text,
                        on_click=self._handle_cancel,
                    ).classes("bg-gray-200 hover:bg-gray-300")

                    ui.button(
                        self.confirm_text,
                        on_click=self._handle_confirm,
                        color="blue",
                    ).classes("bg-blue-600 text-white hover:bg-blue-700")

        return self.dialog

    def _handle_confirm(self):
        """Handle confirm button click."""
        if self.dialog:
            self.dialog.close()
        if self.on_confirm:
            self.on_confirm()

    def _handle_cancel(self):
        """Handle cancel button click."""
        if self.dialog:
            self.dialog.close()
        if self.on_cancel:
            self.on_cancel()

    def show(self):
        """Show the dialog."""
        if self.dialog:
            self.dialog.open()

    def hide(self):
        """Hide the dialog."""
        if self.dialog:
            self.dialog.close()

    def update_message(self, message: str) -> None:
        """
        Update the dialog message.

        Args:
            message: New message text
        """
        self.message = message
        if self.dialog:
            # Find and update the message label
            for child in self.dialog.children:
                if hasattr(child, 'text'):
                    child.text = message

    def update_title(self, title: str) -> None:
        """
        Update the dialog title.

        Args:
            title: New title text
        """
        self.title = title
        if self.dialog:
            # Find and update the title label
            for child in self.dialog.children:
                if hasattr(child, 'text'):
                    child.text = title