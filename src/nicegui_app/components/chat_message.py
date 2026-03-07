# Chat Message Component
"""
Component for displaying individual chat messages in the multi-modal chat interface.
Supports both user and assistant messages with optional document previews.
"""

from typing import Optional, Literal
from nicegui import ui
from datetime import datetime
import markdown

MessageRole = Literal["user", "assistant"]


class ChatMessage:
    """
        A chat message component that displays messages with role indicators,
    timestamps, and optional document previews.

        Attributes:
            role: Either "user" or "assistant" to indicate message sender
            content: The text content of the message
            timestamp: When the message was sent (auto-generated if None)
            document_preview: Optional preview/image for uploaded documents
            show_timestamp: Whether to display the timestamp
    """

    def __init__(
        self,
        role: MessageRole,
        content: str,
        timestamp: Optional[datetime] = None,
        document_preview: Optional[str] = None,
        show_timestamp: bool = True,
    ):
        """
        Initialize a chat message component.

        Args:
            role: Either "user" or "assistant"
            content: Message text content
            timestamp: Optional datetime for the message
            document_preview: Optional base64 image string or URL for document preview
            show_timestamp: Whether to display timestamp
        """
        self.role = role
        self.content = content
        self.timestamp = timestamp if timestamp else datetime.now()
        self.document_preview = document_preview
        self.show_timestamp = show_timestamp

    def render(self):
        """
        Render the chat message as a NiceGUI Card component.

        Returns:
            A styled card containing the message content
        """
        # Create main container card
        card = ui.card().classes("w-full max-w-3xl")

        with card:
            # Message header with role and timestamp
            with ui.row().classes("items-center gap-2 pb-2"):
                # Role indicator
                role_badge = ui.badge(self.role)
                role_badge.classes("capitalize text-xs")

                # Timestamp (if enabled)
                if self.show_timestamp:
                    time_str = self.timestamp.strftime("%H:%M")
                    ui.label(time_str).classes("text-xs text-gray-500")

            # Document preview (if provided)
            if self.document_preview:
                with ui.row().classes("pb-2"):
                    preview_img = ui.image(self.document_preview)
                    preview_img.classes("rounded border max-h-32 object-contain")
                    preview_img.style("max-width: 200px;")

            # Message content with markdown support
            with ui.row():
                message_container = ui.column()
                message_container.classes("gap-1")

                # Convert markdown to HTML and display
                html_content = markdown.markdown(self.content)
                ui.html(html_content).classes("whitespace-pre-wrap")

        return card

    def add_to_parent(self, parent_container):
        """
        Add the rendered card to a parent container.

        Args:
            parent_container: The UI container to add the card to
        """
        if parent_container:
            parent_container.append(self.render())

    def update_content(self, new_content: str) -> None:
        """
        Update the message content and re-render.

        Args:
            new_content: New text content for the message
        """
        if not new_content or not new_content.strip():
            raise ValueError("Content cannot be empty")

        self.content = new_content

    def add_reaction(self, emoji: str) -> None:
        """
        Add a reaction to the message.

        Args:
            emoji: Emoji string to add as reaction (e.g., "👍", "❤️", "🎉")

        Raises:
            ValueError: If emoji is empty or not a valid emoji
        """
        if not emoji or not emoji.strip():
            raise ValueError("Emoji cannot be empty")

        # Validate emoji contains at least one valid emoji character
        # Using regex to check for emoji characters
        import re

        emoji_pattern = r"[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002702-\U000027B0\U000024C2-\U0001F251]"
        if not re.search(emoji_pattern, emoji):
            raise ValueError(f"Invalid emoji: {emoji}")

        # In a real implementation, this would store the reaction
        # and update the UI to show the reaction
        # For now, we'll just log it
        print(f"Added reaction '{emoji}' to message")
