"""Chat interface components."""

from __future__ import annotations

import logging
from typing import Any

import gradio as gr

from sigmahqrag.rag.search import SearchEngine
from sigmahqrag.ui.mode import ChatMode

logger = logging.getLogger(__name__)


class ChatInterface:
    """Chat interface for RAG system."""

    def __init__(
        self,
        search_engine: SearchEngine | None = None,
    ) -> None:
        """Initialize chat interface."""
        self.search_engine = search_engine or SearchEngine()

    async def chat(
        self,
        message: str,
        history: list[list[str]],
        mode: str | None = None,
    ) -> tuple[str, list[list[str]]]:
        """Process chat message and return response.

        Args:
            message: User message
            history: Chat history
            mode: Chat mode (search, coverage, explain)

        Returns:
            Tuple of (response, updated history)
        """
        if not message.strip():
            return "", history

        if mode is None:
            mode = ChatMode.SEARCH.value

        history.append([message, ""])

        if len(history) > 50:
            history = history[-50:]

        try:
            if mode == ChatMode.SEARCH.value:
                response = await self._handle_search(message)
            elif mode == ChatMode.COVERAGE.value:
                response = await self._handle_coverage(message)
            elif mode == ChatMode.EXPLAIN.value:
                response = await self._handle_explain(message)
            else:
                response = await self._handle_search(message)

        except Exception as e:
            logger.error(f"Chat error: {e}")
            response = f"Error: {str(e)}"

        history[-1][1] = response
        return "", history

    async def _handle_search(self, message: str) -> str:
        """Handle search mode."""
        results = await self.search_engine.search(message)

        if results:
            return self._format_response(results)
        return "No results found. Try a different query."

    async def _handle_coverage(self, message: str) -> str:
        """Handle coverage mode."""
        return "Coverage check: Upload a Sigma rule to check coverage."

    async def _handle_explain(self, message: str) -> str:
        """Handle explain mode."""
        return "Explain: Upload a Sigma rule to get explanation."

    def _format_response(self, results: list[dict[str, Any]]) -> str:
        """Format search results as chat response."""
        lines = []
        for i, result in enumerate(results[:5], 1):
            text = result.get("text", "")[:200]
            score = result.get("score", 0)
            citation = self.search_engine.get_citation(result)
            if citation:
                lines.append(f"{i}. {text}... (score: {score:.2f}) [{citation}]")
            else:
                lines.append(f"{i}. {text}... (score: {score:.2f})")

        return "\n\n".join(lines)


def create_chat_component() -> gr.Chatbot:
    """Create chat component."""
    return gr.Chatbot(
        label="Chat History",
        height=400,
    )


def create_input_component() -> gr.Textbox:
    """Create chat input component."""
    return gr.Textbox(
        label="Message",
        placeholder="Ask about Sigma rules...",
        lines=2,
    )
