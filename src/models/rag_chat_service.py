"""
RAG Chat Service for Gradio - Native Integration

Uses native Gradio features:
- Direct LLM service usage
- Simple synchronous generators (queue=True handles async)
- No custom threading infrastructure needed
"""

import logging
from collections.abc import Generator
from typing import Any

from src.core.llm_service import create_llm_service
from src.shared.constants import DATA_MODELS_PATH


class RAGChatService:
    """
    RAG-enhanced chat service for Gradio applications.

    This service combines the LLM and RAG systems to provide context-aware responses.

    Features:
    - Synchronous methods (Gradio queue=True handles async)
    - Simple generator patterns for streaming
    - Direct client usage, no wrappers needed
    """

    def __init__(
        self,
        base_url: str,
        rag_enabled: bool,
        rag_n_results: int,
        rag_min_score: float,
        conversation_history_limit: int,
        model: str = "llama3.2",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """
        Initialize the RAG chat service.

        Args:
            base_url: Base URL for LM Studio server (required - from config)
            rag_enabled: Whether RAG functionality is enabled (required - from config)
            rag_n_results: Number of RAG results to retrieve (required - from config)
            rag_min_score: Minimum similarity score for RAG results (required - from config)
            conversation_history_limit: Maximum number of conversation messages to keep (required - from config)
            model: Model name (optional)
            temperature: Temperature for generation (optional)
            max_tokens: Max tokens for generation (optional)
        """
        self.logger = logging.getLogger(__name__)
        self.rag_enabled = rag_enabled
        self.rag_n_results = rag_n_results
        self.rag_min_score = rag_min_score
        self.conversation_history_limit = conversation_history_limit

        # Initialize LLM client directly (native Gradio approach)
        self.llm_client = create_llm_service(
            base_url=base_url,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # Initialize RAG service (native approach)
        if rag_enabled:
            from src.core.local_embedding_service import create_local_embedding_service

            self.rag_client = create_local_embedding_service()

            # Create ChromaDB collection directly using constant
            from chromadb import PersistentClient

            persist_dir = DATA_MODELS_PATH / "chroma_db"
            persist_dir.mkdir(parents=True, exist_ok=True)

            client = PersistentClient(str(persist_dir))
            self.rag_client.collection = client.get_or_create_collection(
                name="chat_collection",
                metadata={"hnsw:space": "cosine"},
            )
        else:
            self.rag_client = None

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

    def stream_response(
        self,
        user_message: str,
        session_id: str = "default",
        rag_enabled: bool | None = None,
        rag_n_results: int | None = None,
        rag_min_score: float | None = None,
    ) -> Generator[str, None, None]:
        """
        Generate a streaming response to a user message.

        Args:
            user_message: The user's message
            session_id: Session identifier (for history management)
            rag_enabled: Whether to use RAG (overrides default if not None)
            rag_n_results: Number of results for RAG (overrides default if not None)
            rag_min_score: Minimum score for RAG (overrides default if not None)

        Yields:
            Response chunks one character at a time for streaming
        """
        # Determine effective parameters
        use_rag = rag_enabled if rag_enabled is not None else self.rag_enabled
        effective_n_results = (
            rag_n_results if rag_n_results is not None else self.rag_n_results
        )
        effective_min_score = (
            rag_min_score if rag_min_score is not None else self.rag_min_score
        )

        try:
            # Build messages for LLM
            messages: list[dict[str, str]] = []

            if use_rag and self.rag_client:
                # Get RAG context first (synchronous)
                try:
                    context = self.rag_client.query(
                        query_texts=[user_message],
                        n_results=effective_n_results,
                        min_score=effective_min_score,
                    )

                    if context and len(context) > 0:
                        context_text = "\n\n".join(
                            f"[{i+1}] {doc['content']}" for i, doc in enumerate(context)
                        )
                        messages.append(
                            {
                                "role": "user",
                                "content": (
                                    f"Context:\n{context_text}\n\nUser question: {user_message}"
                                ),
                            }
                        )
                    else:
                        messages.append({"role": "user", "content": user_message})
                except Exception as e:
                    self.logger.error(f"RAG context retrieval failed: {e}")
                    messages.append({"role": "user", "content": user_message})
            else:
                messages.append({"role": "user", "content": user_message})

            # Stream response using generator (Gradio handles async with queue=True)
            for chunk in self.llm_client.chat_completion(messages, stream=True):
                if isinstance(chunk, dict) and "content" in chunk:
                    yield chunk["content"]

        except Exception as e:
            self.logger.error(f"Error generating response: {e}")
            yield "I apologize, but I encountered an error while processing your request. Please try again."

    def complete(self, user_message: str) -> str:
        """Get a non-streaming response."""
        try:
            use_rag = self.rag_enabled

            # Build messages for LLM
            messages: list[dict[str, str]] = []

            if use_rag and self.rag_client:
                context = self.rag_client.query(
                    query_texts=[user_message],
                    n_results=self.rag_n_results,
                    min_score=self.rag_min_score,
                )

                if context and len(context) > 0:
                    context_text = "\n\n".join(
                        f"[{i+1}] {doc['content']}" for i, doc in enumerate(context)
                    )
                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"Context:\n{context_text}\n\nUser question: {user_message}"
                            ),
                        }
                    )
                else:
                    messages.append({"role": "user", "content": user_message})
            else:
                messages.append({"role": "user", "content": user_message})

            # Get completion (Gradio queue=True handles async execution)
            response = self.llm_client.chat_completion(messages, stream=False)

            if isinstance(response, dict):
                content = (
                    response.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
            else:
                content = str(response).strip()

            return content
        except Exception as e:
            self.logger.error(f"Error in completion: {e}")
            return "I apologize, but I encountered an error."

    def get_rag_status(self) -> dict[str, Any]:
        """Get the status of the RAG system."""
        status: dict[str, Any] = {
            "rag_enabled": self.rag_enabled,
            "llm_connected": False,
            "collection_name": "chat_collection",
            "document_count": 0,
        }

        if self.rag_client:
            try:
                count_data = self.rag_client.collection.get()
                status["document_count"] = len(count_data["ids"][0])
                status["llm_connected"] = True
            except Exception as e:
                self.logger.error(f"Error getting RAG status: {e}")

        # Test LLM connection
        try:
            result = self.llm_client.chat_completion(
                [{"role": "user", "content": "test"}], stream=False
            )
            if isinstance(result, dict):
                status["llm_connected"] = True
        except Exception as e:
            self.logger.warning(f"LLM not connected: {e}")

        return status

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.rag_client:
                self.rag_client.cleanup()
            # LMStudioClient is a thin wrapper, no cleanup needed
            self.conversation_history.clear()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")


def create_rag_chat_service(
    base_url: str,
    rag_enabled: bool,
    rag_n_results: int,
    rag_min_score: float,
    conversation_history_limit: int,
    model: str = "llama3.2",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> RAGChatService:
    """Create a RAG chat service with specified configuration (all values required from config)."""
    return RAGChatService(
        base_url=base_url,
        rag_enabled=rag_enabled,
        rag_n_results=rag_n_results,
        rag_min_score=rag_min_score,
        conversation_history_limit=conversation_history_limit,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
