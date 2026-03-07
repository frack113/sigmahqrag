"""
Chat Service Layer

Handles message history management and conversation state.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging


class ChatMessage:
    """
    Data structure representing a chat message.

    Attributes:
        id: Unique identifier for the message
        role: Either 'user' or 'assistant'
        content: Text content of the message
        timestamp: When the message was created
        document_path: Optional path to uploaded document
        metadata: Additional message metadata
    """

    def __init__(
        self,
        role: str,
        content: str,
        document_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if role not in ("user", "assistant"):
            raise ValueError("Role must be either 'user' or 'assistant'")

        self.id = str(datetime.now().timestamp()) + f"_{hash(content) % 1000}"
        self.role = role
        self.content = content
        self.timestamp = datetime.now()
        self.document_path = document_path
        self.metadata = metadata or {}


class ChatService:
    """
    Core chat service that manages conversation state.

    Attributes:
        message_history: List of ChatMessage objects in the current session
        max_history: Maximum number of messages to keep in history
        logger: Logging instance for debugging
    """

    def __init__(self, max_history: int = 50) -> None:
        if max_history <= 0:
            raise ValueError("max_history must be a positive integer")

        self.message_history: List[ChatMessage] = []
        self.max_history = max_history
        self.logger = logging.getLogger(__name__)

    def add_message(
        self, role: str, content: str, document_path: Optional[str] = None
    ) -> ChatMessage:
        """
        Add a message to the conversation history.

        Args:
            role: Either 'user' or 'assistant'
            content: Message text content
            document_path: Optional path to uploaded document

        Returns:
            The created ChatMessage object
        """
        message = ChatMessage(role, content, document_path)
        self.message_history.append(message)

        # Trim history if it exceeds max size
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history :]

        return message

    def get_message_history(self, limit: Optional[int] = None) -> List[ChatMessage]:
        """
        Get the conversation history.

        Args:
            limit: Maximum number of messages to return (None for all)

        Returns:
            List of ChatMessage objects
        """
        if limit is None:
            return self.message_history.copy()
        return self.message_history[-limit:]

    def clear_history(self) -> None:
        """Clear the entire conversation history."""
        self.message_history = []

    def export_conversation(self) -> Dict[str, Any]:
        """
        Export the entire conversation history as a dictionary.

        Returns:
            Dictionary containing conversation data
        """
        # Convert messages to serializable format
        messages_data = []
        for msg in self.message_history:
            messages_data.append(
                {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "timestamp": msg.timestamp.isoformat(),
                    "document_path": msg.document_path,
                    "metadata": msg.metadata,
                }
            )

        return {
            "messages": messages_data,
            "exported_at": datetime.now().isoformat(),
            "message_count": len(self.message_history),
        }

    @classmethod
    def import_conversation(cls, data: Dict[str, Any]) -> "ChatService":
        """
        Import conversation from exported data.

        Args:
            data: Dictionary containing exported conversation data

        Returns:
            ChatService instance with imported messages
        """
        service = cls()

        # Reconstruct messages from data
        for msg_data in data["messages"]:
            timestamp_str = msg_data.get("timestamp")
            timestamp = (
                datetime.fromisoformat(timestamp_str)
                if timestamp_str
                else datetime.now()
            )

            message = ChatMessage(
                role=msg_data["role"],
                content=msg_data["content"],
                document_path=msg_data.get("document_path"),
                metadata=msg_data.get("metadata"),
            )
            # Override the generated ID and timestamp with imported values
            message.id = msg_data.get("id", message.id)
            message.timestamp = timestamp
            service.message_history.append(message)

        return service

    async def process_document(self, file_path: str) -> Tuple[str, Optional[str]]:
        """
        Process a document file and extract its content.

        Args:
            file_path: Path to the document file

        Returns:
            Tuple of (document_content, preview_image)
        """
        from .file_processor import FileProcessor

        processor = FileProcessor()
        content = processor.process_file(file_path)

        if content is None:
            raise ValueError(f"Failed to process document: {file_path}")

        # Generate preview for images
        preview = None
        ext = file_path.split(".")[-1].lower()
        if ext in ["png", "jpg", "jpeg"]:
            from ..components.file_upload import FileUpload

            upload_component = FileUpload()
            preview = upload_component.generate_preview(file_path)

        return content, preview
