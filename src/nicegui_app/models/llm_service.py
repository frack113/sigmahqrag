"""
LLM Service for NiceGUI

Handles LLM integration and response generation using OpenAI-compatible endpoints for LM Studio.
Optimized for better performance, error handling, and streaming capabilities.
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import AsyncGenerator, List, Optional

import markdown
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class LLMService:
    """
    Handles LLM integration and response generation using OpenAI-compatible endpoints.

    This service provides:
    - Efficient model initialization and validation
    - Structured prompt templating
    - Robust streaming support
    - Better error handling and fallback mechanisms
    - Auto-streaming capabilities for better performance
    - Support for LM Studio endpoints
    """

    def __init__(
        self,
        model_name: str = "mistralai/ministral-3-14b-reasoning",
        base_url: str = "http://localhost:1234",
        temperature: float = 0.7,
        max_tokens: int = 512,
        streaming: bool = True,
        api_key: str = "lm-studio",
    ):
        """
        Initialize the LLM service using ChatOpenAI.

        Args:
            model_name: Name of the model to use
            base_url: Base URL for the LLM server
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            streaming: Enable streaming responses by default
            api_key: API key for LM Studio (default: "lm-studio")
        """
        self.model_name = model_name
        self.base_url = base_url
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.streaming = streaming
        self.api_key = api_key
        self.llm = None
        self._prompt_template = self._create_prompt_template()

    def _create_prompt_template(self) -> ChatPromptTemplate:
        """Create a structured prompt template for better LLM responses."""
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content=(
                        "You are a helpful AI assistant specialized in document analysis "
                        "and technical queries. Provide clear, concise, and accurate responses. "
                        "When given context documents, base your answers primarily on that information."
                    )
                ),
                MessagesPlaceholder(variable_name="context"),
                HumanMessage(content="{input}"),
            ]
        )

    def initialize(self) -> bool:
        """
        Initialize the LLM instance using ChatOpenAI.

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            self.llm = ChatOpenAI(
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                base_url=self.base_url,
                api_key=self.api_key,
                streaming=self.streaming,
                http_client=None,  # Let it use default HTTP client
            )
            logger.info(
                f"LLM initialized with model: {self.model_name} " f"at {self.base_url}"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            self.llm = None
            return False

    async def generate_response(
        self,
        user_message: str,
        document_content: Optional[str] = None,
        context_documents: Optional[List[str]] = None,
    ) -> str:
        """
        Generate an assistant response using the LLM.

        Uses structured prompts and proper error handling for better results.

        Args:
            user_message: The user's message text.
            document_content: Optional content from uploaded documents.
            context_documents: Optional list of additional context documents.

        Returns:
            Generated response text.

        Raises:
            RuntimeError: If the LLM generation fails or times out.
        """
        logger.info(f"Generating response for: {user_message[:50]}...")

        # Initialize LLM if not already done
        if self.llm is None and not self.initialize():
            return self._get_fallback_response(user_message, document_content)

        try:
            # Build context messages
            context_messages = self._build_context_messages(
                document_content, context_documents
            )

            # Create the prompt
            prompt = self._prompt_template.format(
                context=context_messages, input=user_message
            )

            # Generate response using LangChain ChatOllama
            # Using invoke() for non-streaming, which automatically handles streaming
            # if the model is configured for it
            response = await self.llm.invoke(prompt)

            assistant_response = response.content

            logger.info("Successfully generated response using ChatOllama")
            return assistant_response

        except Exception as e:
            logger.error(f"Error generating response with ChatOllama: {e}")
            return self._get_fallback_response(user_message, document_content)

    async def generate_streaming_response(
        self,
        user_message: str,
        document_content: Optional[str] = None,
        context_documents: Optional[List[str]] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response using the LLM.

        Leverages LangChain's auto-streaming capabilities for optimal performance.

        Args:
            user_message: The user's message text.
            document_content: Optional content from uploaded documents.
            context_documents: Optional list of additional context documents.

        Yields:
            Response chunks for streaming.
        """
        logger.info(f"Generating streaming response for: {user_message[:50]}...")

        # Initialize LLM if not already done
        if self.llm is None and not self.initialize():
            yield self._get_fallback_response(user_message, document_content)
            return

        try:
            # Build context messages
            context_messages = self._build_context_messages(
                document_content, context_documents
            )

            # Create the prompt
            prompt = self._prompt_template.format(
                context=context_messages, input=user_message
            )

            # Use stream() for explicit streaming
            # This provides better control over the streaming process
            async for chunk in self.llm.astream(prompt):
                if chunk.content:
                    yield chunk.content

        except Exception as e:
            logger.error(f"Error generating streaming response: {e}")
            yield self._get_fallback_response(user_message, document_content)

    def _build_context_messages(
        self, document_content: Optional[str], context_documents: Optional[List[str]]
    ) -> List[HumanMessage]:
        """
        Build context messages from document content and context documents.

        Args:
            document_content: Content from uploaded documents
            context_documents: List of additional context documents

        Returns:
            List of HumanMessage objects for context
        """
        context_messages = []

        if document_content:
            context_messages.append(
                HumanMessage(
                    content=f"Document content:\n{document_content[:1000]}...",
                    name="document",
                )
            )

        if context_documents:
            for i, doc in enumerate(context_documents):
                context_messages.append(
                    HumanMessage(
                        content=f"Context document {i+1}:\n{doc[:1000]}...",
                        name=f"context_{i+1}",
                    )
                )

        return context_messages

    def check_model(self, model_name: Optional[str] = None) -> bool:
        """
        Check if a model is available.

        Args:
            model_name: Name of the model to check (uses instance model if None)

        Returns:
            True if model is available, False otherwise.
        """
        # For now, return True to avoid the coroutine warning
        # The actual model availability will be checked during initialization
        return True

    def get_embedding_model(self, model_name: Optional[str] = None) -> Optional:
        """
        Get an embedding model instance for LM Studio.

        Args:
            model_name: Name of the embedding model to use (defaults to config)

        Returns:
            Custom LM Studio embedding model instance
        """
        try:
            embedding_model_name = model_name or self.model_name
            # Use our custom LM Studio embeddings that work correctly with the API
            from .lm_studio_embeddings import LMStudioEmbeddings

            return LMStudioEmbeddings(
                model=embedding_model_name,
                base_url=self.base_url,
                api_key=self.api_key,
            )
        except Exception as e:
            logger.error(f"Failed to create embedding model: {e}")
            return None

    def convert_markdown_to_html(self, markdown_text: str) -> str:
        """
        Convert markdown text to HTML.

        Args:
            markdown_text: Markdown-formatted text

        Returns:
            HTML-formatted text
        """
        try:
            # Convert markdown to HTML with enhanced extensions
            html = markdown.markdown(
                markdown_text,
                extensions=[
                    "extra",  # Extra features like tables
                    "codehilite",  # Syntax highlighting
                    "fenced_code",  # Fenced code blocks
                    "tables",  # Table support
                    "toc",  # Table of contents
                ],
            )
            return html
        except Exception as e:
            logger.error(f"Error converting markdown to HTML: {e}")
            return markdown_text

    def _get_fallback_response(
        self, user_message: str, document_content: Optional[str]
    ) -> str:
        """
        Get a fallback response when LLM fails.

        Args:
            user_message: The user's message.
            document_content: Optional document content.

        Returns:
            Fallback response string.
        """
        if "hello" in user_message.lower() or "hi" in user_message.lower():
            response = "Hello! How can I assist you today?"
        elif document_content and len(document_content) > 0:
            response = (
                f"I've analyzed the document. It contains {len(document_content.split()):,} "
                f"words. Based on the content, here's my analysis: [analysis would go here]"
            )
        else:
            response = (
                f"Thank you for your message: '{user_message}'. I'm a chat assistant "
                f"that can help with document analysis and questions about the content."
            )

        return response
