"""Chat interface components."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import gradio as gr

from src.rag.search import SearchEngine
from src.ui.components.details_panel import DetailsPanel
from src.ui.components.result_card import ResultCard
from src.ui.components.search_bar import SearchBar
from src.ui.mode import ChatMode

logger = logging.getLogger(__name__)

DEFAULT_TOP_K = 10
SEARCH_TIMEOUT = 3.0


class SearchInterface:
    """Search interface with split pane layout."""

    def __init__(
        self,
        search_engine: SearchEngine | None = None,
    ) -> None:
        """Initialize search interface."""
        self.search_engine = search_engine or SearchEngine()
        self.search_bar = SearchBar()
        self.result_card = ResultCard()
        self.details_panel = DetailsPanel()

    async def handle_search(
        self,
        query: str,
    ) -> tuple[list[str], str]:
        """Handle search with live suggestions.

        Args:
            query: User search query

        Returns:
            Tuple of (result cards html list, details markdown)
        """
        if not query or not query.strip():
            return [], DetailsPanel.format_empty_state()

        try:
            results = await asyncio.wait_for(
                self.search_engine.search(query, top_k=DEFAULT_TOP_K),
                timeout=SEARCH_TIMEOUT,
            )

            if not results:
                return [], DetailsPanel.format_empty_state(query)

            card_htmls = []
            for result in results:
                html = ResultCard.format_card(result)
                card_htmls.append(html)

            details = DetailsPanel.format_details(results[0])
            return card_htmls, details

        except TimeoutError:
            logger.error(f"Search timeout for: {query}")
            return [], f"**Timeout:** Search exceeded {SEARCH_TIMEOUT}s"
        except Exception as e:
            logger.error(f"Search error: {e}")
            return [], f"**Error:** {str(e)}"

    async def get_suggestions(self, query: str) -> list[str]:
        """Get live search suggestions.

        Args:
            query: User input

        Returns:
            List of suggestions
        """
        return await self.search_bar.get_suggestions(query)

    def handle_result_click(self, index: int, results_data: list[dict[str, Any]]) -> str:
        """Handle result selection to show details.

        Args:
            index: Selected result index
            results_data: Current results

        Returns:
            Details panel markdown
        """
        if not results_data or index < 0 or index >= len(results_data):
            return DetailsPanel.format_empty_state()
        return DetailsPanel.format_details(results_data[index])


class ChatInterface:
    """Chat interface for RAG system."""

    def __init__(
        self,
        search_engine: SearchEngine | None = None,
    ) -> None:
        """Initialize chat interface."""
        self.search_engine = search_engine or SearchEngine()
        self.search_interface = SearchInterface(search_engine)

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
