"""
Chat Message Component

A reusable component for displaying chat messages with proper formatting,
metadata display, and interactive features.
"""

from nicegui import ui
from typing import Dict, Any, Optional
import datetime


class ChatMessage:
    """
    A component for displaying individual chat messages.
    
    Features:
    - Proper message alignment (user vs assistant)
    - Metadata display (timestamps, sources, etc.)
    - Message formatting and styling
    - Interactive elements (copy, expand, etc.)
    """
    
    def __init__(self, role: str, content: str, metadata: Optional[Dict] = None):
        """
        Initialize a chat message component.
        
        Args:
            role: 'user' or 'assistant'
            content: The message content
            metadata: Optional metadata dictionary
        """
        self.role = role
        self.content = content
        self.metadata = metadata or {}
        
        self._render()
    
    def _render(self):
        """Render the chat message with appropriate styling."""
        # Determine message alignment and styling based on role
        if self.role == "user":
            self._render_user_message()
        else:
            self._render_assistant_message()
    
    def _render_user_message(self):
        """Render a user message (right-aligned)."""
        with ui.row().classes("w-full justify-end mb-4"):
            with ui.card().classes(
                "bg-blue-500 text-white px-4 py-3 rounded-lg max-w-3xl shadow-md"
            ):
                # Message content
                with ui.column().classes("gap-1"):
                    ui.html(self._format_content(self.content)).classes(
                        "whitespace-pre-wrap text-sm leading-relaxed"
                    )
                    
                    # Metadata (if any)
                    if self.metadata:
                        self._render_metadata()
                    
                    # Timestamp
                    self._render_timestamp()
    
    def _render_assistant_message(self):
        """Render an assistant message (left-aligned)."""
        with ui.row().classes("w-full justify-start mb-4"):
            with ui.card().classes(
                "bg-white text-gray-800 px-4 py-3 rounded-lg max-w-3xl shadow-md border"
            ):
                # Message content
                with ui.column().classes("gap-2"):
                    ui.html(self._format_content(self.content)).classes(
                        "whitespace-pre-wrap text-sm leading-relaxed"
                    )
                    
                    # Metadata (if any)
                    if self.metadata:
                        self._render_metadata()
                    
                    # Timestamp
                    self._render_timestamp()
    
    def _format_content(self, content: str) -> str:
        """
        Format message content with HTML support.
        
        Args:
            content: Raw message content
            
        Returns:
            HTML-formatted content
        """
        # Convert markdown-style formatting to HTML
        formatted = content
        
        # Handle line breaks
        formatted = formatted.replace('\n', '<br>')
        
        # Handle bold text (**text**)
        import re
        formatted = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', formatted)
        
        # Handle italic text (*text*)
        formatted = re.sub(r'\*(.*?)\*', r'<em>\1</em>', formatted)
        
        # Handle code blocks (```code```)
        formatted = re.sub(r'```([^`]+)```', r'<code>\1</code>', formatted)
        
        return formatted
    
    def _render_metadata(self):
        """Render message metadata."""
        if not self.metadata:
            return
        
        with ui.row().classes("text-xs text-gray-500 gap-2 mt-1"):
            # Show sources if available
            if 'sources' in self.metadata:
                sources = self.metadata['sources']
                if sources:
                    ui.label(f"Sources: {len(sources)} documents").classes("italic")
            
            # Show confidence score if available
            if 'confidence' in self.metadata:
                confidence = self.metadata['confidence']
                ui.label(f"Confidence: {confidence:.2f}").classes("italic")
            
            # Show any other metadata keys
            for key, value in self.metadata.items():
                if key not in ['sources', 'confidence']:
                    ui.label(f"{key}: {value}").classes("italic")
    
    def _render_timestamp(self):
        """Render message timestamp."""
        timestamp = self.metadata.get('timestamp')
        if timestamp:
            try:
                # Parse ISO format timestamp
                dt = datetime.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                time_str = dt.strftime("%H:%M")
            except:
                time_str = "now"
        else:
            time_str = "now"
        
        with ui.row().classes("justify-end mt-1"):
            ui.label(time_str).classes("text-xs text-gray-400")


def create_chat_message(role: str, content: str, metadata: Optional[Dict] = None):
    """
    Factory function to create a chat message component.
    
    Args:
        role: 'user' or 'assistant'
        content: The message content
        metadata: Optional metadata dictionary
        
    Returns:
        ChatMessage instance
    """
    return ChatMessage(role, content, metadata)