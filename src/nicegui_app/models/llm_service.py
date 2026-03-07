"""
LLM Service for NiceGUI

Handles LLM integration using LangChain's ChatOpenAI.
"""

from typing import List, Optional
import logging
from langchain_openai import ChatOpenAI


class LLMService:
    """
    Handles LLM integration and response generation.

    Methods:
        - generate_response: Generate a response using the LLM
        - build_context: Build context from document content
    """

    def __init__(self, model_name: str = "mistralai/ministral-3-14b-reasoning"):
        """
        Initialize the LLM service.

        Args:
            model_name: Name of the model to use
        """
        self.logger = logging.getLogger(__name__)
        self.model_name = model_name
        self.llm = None

    def initialize(self):
        """Initialize the LLM instance."""
        try:
            self.llm = ChatOpenAI(
                model=self.model_name,
                base_url="http://localhost:1234/v1",
                temperature=0.7,
                max_tokens=1024,
            )
            self.logger.info(f"LLM initialized with model: {self.model_name}")
        except Exception as e:
            self.logger.error(f"Failed to initialize LLM: {e}")
            self.llm = None

    async def generate_response(
        self,
        user_message: str,
        document_content: Optional[str] = None,
        context_documents: Optional[List[str]] = None,
    ) -> str:
        """
        Generate an assistant response using the LLM.

        Args:
            user_message: The user's message text.
            document_content: Optional content from uploaded documents.
            context_documents: Optional list of additional context documents.

        Returns:
            Generated response text.

        Raises:
            Exception: If the LLM generation fails or times out.
        """
        self.logger.info(f"Generating response for: {user_message[:50]}...")

        # Build context from document content if provided
        context = []
        if document_content:
            context.append(f"Document content:\n{document_content[:500]}...")
        if context_documents:
            for i, doc in enumerate(context_documents):
                context.append(f"Context document {i+1}:\n{doc[:500]}...")

        # Create ChatOpenAI instance with local Ollama server
        try:
            llm = ChatOpenAI(
                model=self.model_name,
                base_url="http://localhost:1234/v1",
                temperature=0.7,
                max_tokens=1024,
            )

            # Build the prompt with context
            prompt = self._build_prompt(user_message, context)

            # Generate response using LangChain ChatOpenAI
            response = await llm.ainvoke(prompt)

            # Extract the content from the response
            assistant_response = response.content

            self.logger.info("Successfully generated response using ChatOpenAI")
            return assistant_response

        except Exception as e:
            self.logger.error(f"Error generating response with ChatOpenAI: {e}")
            # Fallback to mock response if LLM fails
            return self._get_fallback_response(user_message, document_content)

    def _build_prompt(self, user_message: str, context: List[str]) -> str:
        """
        Build the prompt for the LLM.

        Args:
            user_message: The user's message.
            context: List of context strings.

        Returns:
            Formatted prompt string.
        """
        context_str = (
            "\n".join(context) if context else "No additional context provided."
        )

        prompt = f"""You are a helpful AI assistant specialized in document analysis and technical queries.

User Question: {user_message}

Context Information:
{context_str}

Please provide a clear, concise, and helpful response to the user's question."""

        return prompt

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
            response = f"I've analyzed the document. It contains {len(document_content.split()):,} words. Based on the content, here's my analysis: [analysis would go here]"
        else:
            response = f"Thank you for your message: '{user_message}'. I'm a chat assistant that can help with document analysis and questions about the content."

        return response

    def check_model(self, model_name: str) -> bool:
        """
        Check if a model is available.

        Args:
            model_name: Name of the model to check.

        Returns:
            True if model is available, False otherwise.
        """
        try:
            # Try to initialize the LLM with the model
            ChatOpenAI(
                model=model_name,
                base_url="http://localhost:1234/v1",
                temperature=0,
                max_tokens=10,
            )
            # If it doesn't raise an error, the model is available
            return True
        except Exception:
            return False
