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
        show_timestamp: bool = True
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
    
    def update_content(self, new_content: str) -> None:
        """
        Update the message content and re-render.
        
        Args:
            new_content: New text content for the message
        """
        self.content = new_content
        # In a real implementation, we would update the UI here
        # For now, this is a placeholder for future functionality
    
    def add_reaction(self, emoji: str) -> None:
        """
        Add a reaction to the message (placeholder for future functionality).
        
        Args:
            emoji: Emoji string to add as reaction
        """
        pass  # To be implemented in future iterations