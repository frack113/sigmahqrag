"""
Chat Service for SigmaHQ RAG application.

Provides RAG-enhanced chat functionality with the optimized LLM and RAG services.
Integrates with the new service architecture for better performance and maintainability.
"""

import asyncio
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.shared import (
    DEFAULT_CONVERSATION_HISTORY_LIMIT,
    SERVICE_CHAT,
    STATUS_DEGRADED,
    STATUS_HEALTHY,
    STATUS_UNHEALTHY,
    AsyncComponent,
    BaseService,
    ChatError,
    ChatMessage,
    LLMError,
    RAGError,
    ValidationResult,
    handle_service_errors,
    retry_with_backoff,
)
from src.core.llm_service import LLMService
from src.core.rag_service import RAGService


@dataclass
class ChatStats:
    """Statistics for chat service."""

    total_conversations: int = 0
    active_conversations: int = 0
    total_messages: int = 0
    successful_responses: int = 0
    failed_responses: int = 0
    average_response_time: float = 0.0
    average_context_retrieval_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    last_error: str | None = None
    uptime_seconds: float = 0.0


class ChatService(BaseService, AsyncComponent):
    """
    RAG-enhanced chat service for SigmaHQ RAG application.

    This service combines the RAG system with the chat interface to provide
    context-aware responses based on stored documents and conversation history.

    Features:
    - RAG-enhanced responses
    - Conversation history management
    - Performance monitoring
    - Error handling and fallbacks
    - Integration with database for persistence
    """

    def __init__(
        self,
        llm_service: LLMService | None = None,
        rag_service: RAGService | None = None,
        conversation_history_limit: int = DEFAULT_CONVERSATION_HISTORY_LIMIT,
    ):
        """
        Initialize the chat service.

        Args:
            llm_service: Pre-configured LLM service
            rag_service: Pre-configured RAG service
            conversation_history_limit: Maximum number of conversation messages to keep
        """
        BaseService.__init__(self, f"{SERVICE_CHAT}.chat_service")
        AsyncComponent.__init__(self)

        # Services
        self.llm_service = llm_service
        self.rag_service = rag_service

        # Configuration
        self.conversation_history_limit = conversation_history_limit

        # Conversation history
        self.conversations: dict[str, list[ChatMessage]] = {}

        # Statistics
        self.stats = ChatStats()
        self._start_time = datetime.now()

        # Service state
        self._initialized = False

    async def initialize(self) -> bool:
        """
        Initialize the chat service.

        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True

        try:
            # Initialize LLM service if not provided
            if self.llm_service is None:
                self.llm_service = LLMService()
                await self.llm_service.initialize()

            # Initialize RAG service if not provided
            if self.rag_service is None:
                self.rag_service = RAGService(llm_service=self.llm_service)
                await self.rag_service.initialize()

            self._initialized = True
            self._log_operation("Chat service initialization", True)
            self.logger.info("Chat service initialized successfully")
            return True

        except Exception as e:
            self._log_operation("Chat service initialization", False, {"error": str(e)})
            self.logger.error(f"Chat service initialization failed: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            # Clean up conversations
            self.conversations.clear()

            # Clean up services
            if self.llm_service:
                self.llm_service.cleanup()
            if self.rag_service:
                self.rag_service.cleanup()

            self._initialized = False
            self._log_operation("Chat service cleanup", True)

        except Exception as e:
            self._log_operation("Chat service cleanup", False, {"error": str(e)})
            self.logger.error(f"Error during chat service cleanup: {e}")

    def add_message_to_history(self, session_id: str, role: str, content: str) -> None:
        """
        Add a message to the conversation history.

        Args:
            session_id: Session identifier
            role: Role of the message (user or assistant)
            content: Content of the message
        """
        if session_id not in self.conversations:
            self.conversations[session_id] = []

        message = ChatMessage(
            role=role, content=content, timestamp=datetime.now(), metadata={}
        )

        self.conversations[session_id].append(message)

        # Limit conversation history size
        if len(self.conversations[session_id]) > self.conversation_history_limit:
            # Remove oldest messages, but keep at least the last few
            self.conversations[session_id] = self.conversations[session_id][
                -self.conversation_history_limit :
            ]

    def clear_conversation_history(self, session_id: str | None = None) -> None:
        """
        Clear the conversation history.

        Args:
            session_id: Session identifier (if None, clears all conversations)
        """
        if session_id:
            if session_id in self.conversations:
                del self.conversations[session_id]
                self.logger.info(
                    f"Conversation history cleared for session: {session_id}"
                )
        else:
            self.conversations.clear()
            self.logger.info("All conversation history cleared")

    def get_conversation_history(self, session_id: str) -> list[dict[str, str]]:
        """
        Get the current conversation history.

        Args:
            session_id: Session identifier

        Returns:
            List of conversation messages
        """
        if session_id not in self.conversations:
            return []

        return [
            {
                "role": msg["role"],
                "content": msg["content"],
                "timestamp": msg["timestamp"].isoformat(),
                "metadata": msg.get("metadata", {}),
            }
            for msg in self.conversations[session_id]
        ]

    def get_session_ids(self) -> list[str]:
        """Get all active session IDs."""
        return list(self.conversations.keys())

    def get_session_message_count(self, session_id: str) -> int:
        """Get the number of messages in a session."""
        return len(self.conversations.get(session_id, []))

    @handle_service_errors(
        error_types=[RAGError, LLMError, ChatError],
        default_message="Chat response generation failed",
    )
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    async def generate_response(
        self,
        user_message: str,
        session_id: str = "default",
        system_prompt: str | None = None,
        use_rag: bool | None = None,
        rag_n_results: int = 3,
        rag_min_score: float = 0.1,
    ) -> str:
        """
        Generate a response to a user message with improved timeout handling and fallbacks.

        Args:
            user_message: The user's message
            session_id: Session identifier
            system_prompt: Optional system prompt
            use_rag: Whether to use RAG (overrides default setting)
            rag_n_results: Number of RAG results to retrieve
            rag_min_score: Minimum similarity score for RAG results

        Returns:
            The generated response
        """
        start_time = time.time()

        try:
            # Determine if RAG should be used
            should_use_rag = (
                use_rag if use_rag is not None else (self.rag_service is not None)
            )

            # Add user message to history
            self.add_message_to_history(session_id, "user", user_message)

            if should_use_rag and self.rag_service:
                # Use RAG-enhanced response generation with timeout
                try:
                    # Retrieve context with timeout
                    context_start = time.time()
                    relevant_docs, metadata = await asyncio.wait_for(
                        self.rag_service.retrieve_context(
                            query=user_message,
                            n_results=rag_n_results,
                            min_relevance_score=rag_min_score,
                        ),
                        timeout=25.0,  # 25 seconds timeout for RAG operations
                    )
                    context_time = time.time() - context_start

                    # Build context string
                    if relevant_docs:
                        context_text = "\n\n".join(relevant_docs)
                        # Limit context length to avoid token limits
                        if len(context_text) > 4000:
                            context_text = context_text[:4000] + "..."

                        # Create enhanced prompt with context
                        enhanced_prompt = f"""Use the following context to answer the question:

Context:
{context_text}

Question: {user_message}

Answer concisely and accurately based on the provided context."""
                    else:
                        # No relevant context found, use original query
                        enhanced_prompt = user_message

                    # Generate response using LLM service with timeout
                    try:
                        response = await asyncio.wait_for(
                            self.llm_service.simple_completion(
                                prompt=enhanced_prompt, system_prompt=system_prompt
                            ),
                            timeout=30.0,  # 30 seconds timeout for LLM completion
                        )
                    except asyncio.TimeoutError:
                        self.logger.warning(
                            "LLM response timed out, using simple completion"
                        )
                        # Fallback to simple completion without context
                        response = await self.llm_service.simple_completion(
                            prompt=user_message, system_prompt=system_prompt
                        )

                    # Update context retrieval time statistics
                    if self.stats.total_conversations > 0:
                        self.stats.average_context_retrieval_time = (
                            (
                                self.stats.average_context_retrieval_time
                                * (self.stats.total_conversations - 1)
                            )
                            + context_time
                        ) / self.stats.total_conversations
                    else:
                        self.stats.average_context_retrieval_time = context_time

                except asyncio.TimeoutError:
                    self.logger.warning(
                        "RAG context retrieval timed out, falling back to standard LLM"
                    )
                    # Fallback to standard LLM response
                    try:
                        response = await asyncio.wait_for(
                            self.llm_service.simple_completion(
                                prompt=user_message, system_prompt=system_prompt
                            ),
                            timeout=30.0,
                        )
                    except asyncio.TimeoutError:
                        response = "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."
                except Exception as rag_error:
                    self.logger.error(
                        f"RAG response failed: {rag_error}, falling back to standard LLM"
                    )
                    # Fallback to standard LLM response
                    try:
                        response = await asyncio.wait_for(
                            self.llm_service.simple_completion(
                                prompt=user_message, system_prompt=system_prompt
                            ),
                            timeout=30.0,
                        )
                    except asyncio.TimeoutError:
                        response = "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."
            else:
                # Use standard LLM response generation
                try:
                    response = await asyncio.wait_for(
                        self.llm_service.simple_completion(
                            prompt=user_message, system_prompt=system_prompt
                        ),
                        timeout=30.0,
                    )
                except asyncio.TimeoutError:
                    response = "I apologize, but I'm experiencing technical difficulties. Please try again in a moment."

            # Add assistant response to history
            self.add_message_to_history(session_id, "assistant", response)

            # Update statistics
            self.stats.total_conversations += 1
            self.stats.active_conversations = len(self.conversations)
            self.stats.total_messages += 2  # User + assistant message
            self.stats.successful_responses += 1

            response_time = time.time() - start_time

            # Update average response time (moving average)
            if self.stats.successful_responses > 1:
                self.stats.average_response_time = (
                    (
                        self.stats.average_response_time
                        * (self.stats.successful_responses - 1)
                    )
                    + response_time
                ) / self.stats.successful_responses
            else:
                self.stats.average_response_time = response_time

            return response

        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            error_response = "I apologize, but I encountered an error while processing your request. Please try again."
            self.add_message_to_history(session_id, "assistant", error_response)
            self.stats.failed_responses += 1
            self.stats.last_error = str(e)
            return error_response

    async def generate_streaming_response(
        self,
        user_message: str,
        session_id: str = "default",
        system_prompt: str | None = None,
        use_rag: bool | None = None,
        rag_n_results: int = 3,
        rag_min_score: float = 0.1,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response to a user message.

        Args:
            user_message: The user's message
            session_id: Session identifier
            system_prompt: Optional system prompt
            use_rag: Whether to use RAG (overrides default setting)
            rag_n_results: Number of RAG results to retrieve
            rag_min_score: Minimum similarity score for RAG results

        Yields:
            Response chunks for streaming
        """
        start_time = time.time()

        try:
            # Determine if RAG should be used
            should_use_rag = (
                use_rag if use_rag is not None else (self.rag_service is not None)
            )

            # Add user message to history
            self.add_message_to_history(session_id, "user", user_message)

            if should_use_rag and self.rag_service:
                # Use RAG-enhanced streaming response generation
                response_generator = self.rag_service.generate_streaming_rag_response(
                    query=user_message,
                    system_prompt=system_prompt,
                    n_results=rag_n_results,
                    min_relevance_score=rag_min_score,
                )

                # Always treat it as an async generator and use async for
                if hasattr(response_generator, "__aiter__"):
                    async for chunk in response_generator:
                        yield chunk
                else:
                    # Fallback: if it's not an async generator, it should be a coroutine
                    try:
                        # This should be a coroutine, so we can await it
                        if asyncio.iscoroutine(response_generator):
                            response = await response_generator
                            yield response
                        else:
                            # If it's neither async generator nor coroutine, handle gracefully
                            yield "Error: Invalid response type from RAG service"
                    except TypeError as e:
                        # If it's neither, handle gracefully
                        yield f"Error: {str(e)}"
            else:
                # Use standard LLM streaming response generation
                response_generator = self.llm_service.streaming_completion(
                    prompt=user_message, system_prompt=system_prompt
                )

                # Always treat it as an async generator and use async for
                if hasattr(response_generator, "__aiter__"):
                    async for chunk in response_generator:
                        yield chunk
                else:
                    # Fallback: if it's not an async generator, it should be a coroutine
                    try:
                        # This should be a coroutine, so we can await it
                        if asyncio.iscoroutine(response_generator):
                            response = await response_generator
                            yield response
                        else:
                            # If it's neither async generator nor coroutine, handle gracefully
                            yield "Error: Invalid response type from LLM service"
                    except TypeError as e:
                        # If it's neither, handle gracefully
                        yield f"Error: {str(e)}"

            # Update statistics
            self.stats.total_conversations += 1
            self.stats.active_conversations = len(self.conversations)
            self.stats.total_messages += 2  # User + assistant message
            self.stats.successful_responses += 1

            response_time = time.time() - start_time

            # Update average response time (moving average)
            if self.stats.successful_responses > 1:
                self.stats.average_response_time = (
                    (
                        self.stats.average_response_time
                        * (self.stats.successful_responses - 1)
                    )
                    + response_time
                ) / self.stats.successful_responses
            else:
                self.stats.average_response_time = response_time

        except Exception as e:
            self.logger.error(f"Error generating streaming response: {e}")
            error_message = "I apologize, but I encountered an error while processing your request. Please try again."
            self.add_message_to_history(session_id, "assistant", error_message)
            self.stats.failed_responses += 1
            self.stats.last_error = str(e)
            yield error_message

    def get_rag_status(self) -> dict[str, Any]:
        """
        Get the status of the RAG system.

        Returns:
            Dictionary with RAG status information
        """
        status = {
            "rag_enabled": self.rag_service is not None,
            "conversation_history_count": len(self.conversations),
            "conversation_history_limit": self.conversation_history_limit,
        }

        if self.rag_service:
            try:
                status["rag_service_available"] = self.rag_service.check_availability()
                if status["rag_service_available"]:
                    rag_stats = self.rag_service.get_context_stats()
                    cache_stats = self.rag_service.get_cache_stats()
                    status.update(rag_stats)
                    status["cache_stats"] = cache_stats
            except Exception as e:
                self.logger.error(f"Error getting RAG status: {e}")
                status["rag_service_available"] = False

        return status

    async def clear_rag_context(self) -> bool:
        """
        Clear the RAG context (stored documents).

        Returns:
            True if successful, False otherwise
        """
        if self.rag_service:
            try:
                success = await self.rag_service.clear_context()
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
            "rag_enabled": self.rag_service is not None,
            "conversation_history_count": len(self.conversations),
        }

        if self.rag_service:
            try:
                rag_stats = self.rag_service.get_usage_stats()
                cache_stats = self.rag_service.get_cache_stats()
                stats.update(rag_stats)
                stats["cache_stats"] = cache_stats
            except Exception as e:
                self.logger.error(f"Error getting RAG stats: {e}")
                stats["error"] = str(e)

        return stats

    def get_health_status(self) -> dict[str, Any]:
        """Get service health status."""
        status = STATUS_HEALTHY
        issues = []

        # Check LLM service availability
        if self.llm_service:
            llm_status = self.llm_service.get_health_status()
            if llm_status["status"] != STATUS_HEALTHY:
                status = STATUS_DEGRADED
                issues.append(f"LLM service degraded: {llm_status.get('issues', [])}")
        else:
            status = STATUS_UNHEALTHY
            issues.append("LLM service not available")

        # Check RAG service availability
        if self.rag_service:
            rag_status = self.rag_service.get_health_status()
            if rag_status["status"] != STATUS_HEALTHY:
                status = STATUS_DEGRADED
                issues.append(f"RAG service degraded: {rag_status.get('issues', [])}")

        # Check error rate
        if self.stats.total_conversations > 0:
            error_rate = self.stats.failed_responses / self.stats.total_conversations
            if error_rate > 0.1:  # More than 10% error rate
                status = STATUS_DEGRADED
                issues.append(f"High error rate: {error_rate:.2%}")

        # Check response time
        if self.stats.average_response_time > 30.0:  # More than 30 seconds average
            status = STATUS_DEGRADED
            issues.append(
                f"High response time: {self.stats.average_response_time:.2f}s"
            )

        # Check memory usage
        if self.stats.memory_usage_mb > 1024.0:  # More than 1GB
            status = STATUS_DEGRADED
            issues.append(f"High memory usage: {self.stats.memory_usage_mb:.2f}MB")

        return {
            "service": SERVICE_CHAT,
            "status": status,
            "issues": issues,
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "total_conversations": self.stats.total_conversations,
                "active_conversations": self.stats.active_conversations,
                "total_messages": self.stats.total_messages,
                "successful_responses": self.stats.successful_responses,
                "failed_responses": self.stats.failed_responses,
                "average_response_time": self.stats.average_response_time,
                "average_context_retrieval_time": self.stats.average_context_retrieval_time,
                "memory_usage_mb": self.stats.memory_usage_mb,
                "cpu_usage_percent": self.stats.cpu_usage_percent,
                "last_error": self.stats.last_error,
                "uptime_seconds": self.stats.uptime_seconds,
            },
            "rag_status": self.get_rag_status(),
        }

    def get_usage_stats(self) -> dict[str, Any]:
        """Get comprehensive usage statistics."""
        return {
            "conversation_history_limit": self.conversation_history_limit,
            "active_sessions": len(self.conversations),
            "total_messages": sum(
                len(history) for history in self.conversations.values()
            ),
            "stats": {
                "total_conversations": self.stats.total_conversations,
                "active_conversations": self.stats.active_conversations,
                "total_messages": self.stats.total_messages,
                "successful_responses": self.stats.successful_responses,
                "failed_responses": self.stats.failed_responses,
                "average_response_time": self.stats.average_response_time,
                "average_context_retrieval_time": self.stats.average_context_retrieval_time,
                "memory_usage_mb": self.stats.memory_usage_mb,
                "cpu_usage_percent": self.stats.cpu_usage_percent,
                "last_error": self.stats.last_error,
                "uptime_seconds": self.stats.uptime_seconds,
            },
            "rag_stats": self.get_rag_stats(),
        }

    def validate_session_id(self, session_id: str) -> ValidationResult:
        """
        Validate a session ID.

        Args:
            session_id: Session identifier to validate

        Returns:
            Validation result
        """
        if not session_id or not session_id.strip():
            return ValidationResult(
                is_valid=False, errors=["Session ID cannot be empty"], warnings=[]
            )

        if len(session_id) > 100:
            return ValidationResult(
                is_valid=False,
                errors=["Session ID too long (max 100 characters)"],
                warnings=[],
            )

        # Check for valid characters (alphanumeric, hyphens, underscores)
        import re

        if not re.match(r"^[a-zA-Z0-9_-]+$", session_id):
            return ValidationResult(
                is_valid=False,
                errors=["Session ID contains invalid characters"],
                warnings=["Use only letters, numbers, hyphens, and underscores"],
            )

        return ValidationResult(is_valid=True, errors=[], warnings=[])

    def get_session_summary(self, session_id: str) -> dict[str, Any]:
        """
        Get a summary of a session.

        Args:
            session_id: Session identifier

        Returns:
            Session summary
        """
        if session_id not in self.conversations:
            return {
                "session_id": session_id,
                "exists": False,
                "message_count": 0,
                "duration": 0,
                "first_message": None,
                "last_message": None,
            }

        messages = self.conversations[session_id]

        if not messages:
            return {
                "session_id": session_id,
                "exists": True,
                "message_count": 0,
                "duration": 0,
                "first_message": None,
                "last_message": None,
            }

        first_message = messages[0]
        last_message = messages[-1]
        duration = (
            last_message["timestamp"] - first_message["timestamp"]
        ).total_seconds()

        return {
            "session_id": session_id,
            "exists": True,
            "message_count": len(messages),
            "duration": duration,
            "first_message": {
                "role": first_message["role"],
                "content": (
                    first_message["content"][:100] + "..."
                    if len(first_message["content"]) > 100
                    else first_message["content"]
                ),
                "timestamp": first_message["timestamp"].isoformat(),
            },
            "last_message": {
                "role": last_message["role"],
                "content": (
                    last_message["content"][:100] + "..."
                    if len(last_message["content"]) > 100
                    else last_message["content"]
                ),
                "timestamp": last_message["timestamp"].isoformat(),
            },
        }

    def update_config(self, new_config: dict[str, Any]) -> bool:
        """Update chat service configuration."""
        try:
            if "conversation_history_limit" in new_config:
                self.conversation_history_limit = new_config[
                    "conversation_history_limit"
                ]

            self.logger.info(f"Chat service configuration updated: {new_config}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update chat service configuration: {e}")
            return False


# Convenience factory function
def create_chat_service(
    llm_service: LLMService | None = None,
    rag_service: RAGService | None = None,
    conversation_history_limit: int = DEFAULT_CONVERSATION_HISTORY_LIMIT,
) -> ChatService:
    """Create a chat service with default configuration."""
    return ChatService(
        llm_service=llm_service,
        rag_service=rag_service,
        conversation_history_limit=conversation_history_limit,
    )


# Backward compatibility alias
RAGChatService = ChatService
