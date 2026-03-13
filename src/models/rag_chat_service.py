"""
RAG Chat Service for Gradio

Integrates RAG functionality with the chat interface to provide context-aware responses.
Uses the optimized RAG service and LLM service for enhanced chat capabilities.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Any

from .llm_service import LLMService
from .rag_service import RAGService


class RAGChatService:
    """
    RAG-enhanced chat service for NiceGUI applications.

    This service combines the RAG system with the chat interface to provide
    context-aware responses based on stored documents and conversation history.
    """

    def __init__(
        self,
        llm_service: LLMService | None = None,
        rag_service: RAGService | None = None,
        base_url: str = "http://localhost:1234",
        rag_enabled: bool = True,
        rag_n_results: int = 3,
        rag_min_score: float = 0.1,
        conversation_history_limit: int = 10,
    ):
        """
        Initialize the RAG chat service.

        Args:
            llm_service: Pre-configured LLM service
            rag_service: Pre-configured RAG service
            base_url: Base URL for LM Studio server
            rag_enabled: Whether RAG functionality is enabled
            rag_n_results: Number of RAG results to retrieve
            rag_min_score: Minimum similarity score for RAG results
            conversation_history_limit: Maximum number of conversation messages to keep
        """
        self.logger = logging.getLogger(__name__)
        self.rag_enabled = rag_enabled
        self.rag_n_results = rag_n_results
        self.rag_min_score = rag_min_score
        self.conversation_history_limit = conversation_history_limit

        # Initialize LLM service
        self.llm_service = llm_service or LLMService(
            config={
                "model": "qwen/qwen3.5-9b",
                "base_url": base_url,
                "api_key": "lm-studio",
                "temperature": 0.7,
                "max_tokens": 512,
                "enable_streaming": True,
            }
        )

        # Initialize RAG service
        if rag_enabled:
            self.rag_service = rag_service or RAGService(
                llm_service=self.llm_service,
                config={
                    "model": "text-embedding-all-minilm-l6-v2-embedding",
                    "base_url": base_url,
                    "api_key": "lm-studio",
                    "chunk_size": 1000,
                    "chunk_overlap": 200,
                    "collection_name": "chat_collection",
                },
                database_config={
                    "path": "./data/.chromadb",
                    "max_connections": 5,
                    "timeout": 30,
                },
            )
        else:
            self.rag_service = None

        # Conversation history
        self.conversation_history: list[dict[str, str]] = []

    def add_message_to_history(self, role: str, content: str) -> None:
        """
        Add a message to the conversation history.

        Args:
            role: Role of the message (user or assistant)
            content: Content of the message
        """
        self.conversation_history.append({"role": role, "content": content})

        # Limit conversation history size
        if len(self.conversation_history) > self.conversation_history_limit:
            # Remove oldest messages, but keep at least the last few
            self.conversation_history = self.conversation_history[
                -self.conversation_history_limit :
            ]

    def clear_conversation_history(self) -> None:
        """Clear the conversation history."""
        self.conversation_history.clear()
        self.logger.info("Conversation history cleared")

    def get_conversation_history(self) -> list[dict[str, str]]:
        """
        Get the current conversation history.

        Returns:
            List of conversation messages
        """
        return self.conversation_history.copy()

    async def generate_response(
        self,
        user_message: str,
        system_prompt: str | None = None,
        use_rag: bool | None = None,
    ) -> str:
        """
        Generate a response to a user message with improved timeout handling.

        Args:
            user_message: The user's message
            system_prompt: Optional system prompt
            use_rag: Whether to use RAG (overrides default setting)

        Returns:
            The generated response
        """
        # Determine if RAG should be used
        should_use_rag = use_rag if use_rag is not None else self.rag_enabled

        try:
            if should_use_rag and self.rag_service:
                # Use RAG-enhanced response generation with timeout
                try:
                    import asyncio

                    response_task = asyncio.create_task(
                        self.rag_service.generate_rag_response(
                            query=user_message,
                            system_prompt=system_prompt,
                            n_results=self.rag_n_results,
                            min_relevance_score=self.rag_min_score,
                        )
                    )
                    # Set timeout for RAG operations (25 seconds)
                    response = await asyncio.wait_for(response_task, timeout=25.0)
                except asyncio.TimeoutError:
                    self.logger.warning(
                        "RAG response timed out, falling back to standard LLM"
                    )
                    # Fallback to standard LLM response
                    response = self.llm_service.simple_completion(
                        prompt=user_message, system_prompt=system_prompt
                    )
                except Exception as rag_error:
                    self.logger.error(
                        f"RAG response failed: {rag_error}, falling back to standard LLM"
                    )
                    # Fallback to standard LLM response
                    response = self.llm_service.simple_completion(
                        prompt=user_message, system_prompt=system_prompt
                    )
            else:
                # Use standard LLM response generation
                response = self.llm_service.simple_completion(
                    prompt=user_message, system_prompt=system_prompt
                )

            # Add messages to conversation history
            self.add_message_to_history("user", user_message)
            self.add_message_to_history("assistant", response)

            return response

        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            error_response = "I apologize, but I encountered an error while processing your request. Please try again."
            self.add_message_to_history("user", user_message)
            self.add_message_to_history("assistant", error_response)
            return error_response

    async def generate_streaming_response(
        self,
        user_message: str,
        system_prompt: str | None = None,
        use_rag: bool | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response to a user message.

        Args:
            user_message: The user's message
            system_prompt: Optional system prompt
            use_rag: Whether to use RAG (overrides default setting)

        Yields:
            Response chunks for streaming
        """
        # Determine if RAG should be used
        should_use_rag = use_rag if use_rag is not None else self.rag_enabled

        try:
            if should_use_rag and self.rag_service:
                # Use RAG-enhanced streaming response generation
                async for chunk in self.rag_service.generate_streaming_rag_response(
                    query=user_message,
                    system_prompt=system_prompt,
                    n_results=self.rag_n_results,
                    min_relevance_score=self.rag_min_score,
                ):
                    yield chunk
            else:
                # Use standard LLM streaming response generation
                async for chunk in self.llm_service.streaming_completion(
                    prompt=user_message, system_prompt=system_prompt
                ):
                    yield chunk

        except Exception as e:
            self.logger.error(f"Error generating streaming response: {e}")
            error_message = "I apologize, but I encountered an error while processing your request. Please try again."
            yield error_message

    def get_rag_status(self) -> dict[str, Any]:
        """
        Get the status of the RAG system.

        Returns:
            Dictionary with RAG status information
        """
        status = {
            "rag_enabled": self.rag_enabled,
            "rag_service_available": False,
            "conversation_history_count": len(self.conversation_history),
            "conversation_history_limit": self.conversation_history_limit,
        }

        if self.rag_service:
            try:
                status["rag_service_available"] = self.rag_service.check_availability()
                if status["rag_service_available"]:
                    rag_stats = self.rag_service.get_context_stats()
                    status.update(rag_stats)
            except Exception as e:
                self.logger.error(f"Error getting RAG status: {e}")
                status["rag_service_available"] = False

        return status

    def clear_rag_context(self) -> bool:
        """
        Clear the RAG context (stored documents).

        Returns:
            True if successful, False otherwise
        """
        if self.rag_service:
            try:
                success = self.rag_service.clear_context()
                if success:
                    self.logger.info("RAG context cleared")
                return success
            except Exception as e:
                self.logger.error(f"Error clearing RAG context: {e}")
                return False
        return False

    def get_rag_stats(self) -> dict[str, Any]:
        """
        Get RAG statistics.

        Returns:
            Dictionary with RAG statistics
        """
        stats = {
            "rag_enabled": self.rag_enabled,
            "conversation_history_count": len(self.conversation_history),
        }

        if self.rag_service:
            try:
                rag_stats = self.rag_service.get_context_stats()
                cache_stats = self.rag_service.get_cache_stats()
                stats.update(rag_stats)
                stats["cache_stats"] = cache_stats
            except Exception as e:
                self.logger.error(f"Error getting RAG stats: {e}")
                stats["error"] = str(e)

        return stats

    def get_stats(self) -> dict[str, Any]:
        """
        Get comprehensive statistics (alias for get_rag_stats for backward compatibility).

        Returns:
            Dictionary with comprehensive statistics
        """
        return self.get_rag_stats()

    def cleanup(self):
        """Clean up resources."""
        try:
            if self.rag_service:
                self.rag_service.cleanup()
            self.llm_service.cleanup()
            self.conversation_history.clear()
        except Exception as e:
            self.logger.error(f"Error during RAG chat service cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


# Convenience factory function
def create_rag_chat_service(
    base_url: str = "http://localhost:1234",
    rag_enabled: bool = True,
    rag_n_results: int = 3,
    rag_min_score: float = 0.1,
    conversation_history_limit: int = 10,
) -> RAGChatService:
    """Create a RAG chat service with default configuration."""
    return RAGChatService(
        base_url=base_url,
        rag_enabled=rag_enabled,
        rag_n_results=rag_n_results,
        rag_min_score=rag_min_score,
        conversation_history_limit=conversation_history_limit,
    )
