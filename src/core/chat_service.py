"""
Chat Service - RAG-enhanced chat functionality

Integrates RAG with chat service to provide context-aware responses.
"""

import logging
from typing import Any

from src.core.rag_service import RAGService
from .llm_service import LLMService


class ChatService:
    """RAG-enhanced chat service."""

    def __init__(
        self,
        llm_service: LLMService,
        rag_service: RAGService | None = None,
        conversation_history_limit: int = 10,
        logger=None,
    ):
        """Initialize chat service."""
        self.llm_service = llm_service
        self.rag_service = rag_service
        self.conversation_history_limit = conversation_history_limit
        self.conversation_history: list[dict[str, str]] = []

        if logger is None:
            self.logger = logging.getLogger(__name__)
        else:
            self.logger = logger

    def add_message(self, role: str, content: str) -> None:
        """Add message to conversation history."""
        self.conversation_history.append({"role": role, "content": content})

    def get_conversation_history(self) -> list[dict[str, str]]:
        """Get conversation history."""
        return self.conversation_history[-self.conversation_history_limit:]

    async def chat(self, user_message: str) -> str:
        """Generate a response to user message."""
        try:
            # Get RAG context if available
            context = []
            if self.rag_service:
                results = await self.rag_service.query(user_message)
                if results:
                    context = [f"[{i+1}] {doc['content']}" for i, doc in enumerate(results[:3])]

            # Build messages
            system_prompt = "You are SigmaHQ RAG assistant. Use the provided context to answer questions."
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context: {'\n'.join(context) if context else 'No additional context.'}\n\nQuestion: {user_message}"},
            ]

            # Get response from LLM
            result = await self.llm_service.chat_completion(messages, stream=False)
            return result.get("choices", [{}])[0].get("message", {}).get("content", "").strip() or "I apologize, but I couldn't generate a response."

        except Exception as e:
            self.logger.error(f"Error in chat: {e}")
            return "I apologize, but I encountered an error. Please try again."

    async def stream_chat(self, user_message: str) -> None:
        """Stream chat responses character by character."""
        try:
            # Get RAG context if available
            context = []
            if self.rag_service:
                results = await self.rag_service.query(user_message)
                if results:
                    context = [f"[{i+1}] {doc['content']}" for i, doc in enumerate(results[:3])]

            # Build messages
            system_prompt = "You are SigmaHQ RAG assistant. Use the provided context to answer questions."
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Context: {'\n'.join(context) if context else 'No additional context.'}\n\nQuestion: {user_message}"},
            ]

            # Stream response
            result = await self.llm_service.chat_completion(messages, stream=True)
            for chunk in result:
                yield chunk

        except Exception as e:
            self.logger.error(f"Error in stream_chat: {e}")
            yield "I apologize, but I encountered an error. Please try again."

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history.clear()