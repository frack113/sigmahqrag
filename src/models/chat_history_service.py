# This file has been deprecated.
# ChatHistoryService functionality has been integrated into src/core/chat_service.py
# and database persistence is handled by src/infrastructure/database_setup.py
# Keep for backward compatibility only

from typing import Any


class ChatHistoryService:
    """
    Deprecated: Chat history functionality is now managed by ChatService.
    Database persistence is handled by DatabaseSetup.
    """

    def __init__(self, db_path: str | None = None, max_messages: int = 1000):
        """Deprecated - use ChatService instead."""
        pass

    def save_message(self, role: str, content: str, metadata: dict | None = None) -> bool:
        """Use ChatService.add_message_to_history() instead."""
        raise DeprecationWarning("Use ChatService.add_message_to_history() instead")

    def get_session_history(self, limit: int | None = None) -> list[dict[str, Any]]:
        """Use ChatService.get_conversation_history() instead."""
        raise DeprecationWarning("Use ChatService.get_conversation_history() instead")


# Backward compatibility - import from core services
try:
    from src.core.chat_service import ChatService

    _chat_service = None

    @classmethod
    def get_instance(cls) -> ChatService:
        """Get the global ChatService instance."""
        return cls._service
except ImportError:
    pass