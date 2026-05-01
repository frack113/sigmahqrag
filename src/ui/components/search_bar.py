"""Search bar component."""

from __future__ import annotations

import logging

import gradio as gr

from src.rag.search import SearchEngine

logger = logging.getLogger(__name__)

DEBOUNCE_MS = 300
MIN_CHARS_FOR_SUGGESTIONS = 2
MAX_SUGGESTIONS = 5


class SearchBar:
    """Search bar component with live suggestions."""

    def __init__(self) -> None:
        """Initialize the search bar."""
        self.search_engine = SearchEngine()
        self.component = gr.Textbox(
            label="Search",
            placeholder="Enter your query...",
            lines=1,
        )

    def get_component(self) -> gr.Component:
        """Get the component."""
        return self.component

    async def get_suggestions(self, query: str) -> list[str]:
        """Get live search suggestions.

        Args:
            query: User input

        Returns:
            List of suggestions
        """
        if not query or len(query.strip()) < MIN_CHARS_FOR_SUGGESTIONS:
            return []

        try:
            results = await self.search_engine.search(query, top_k=MAX_SUGGESTIONS)
            suggestions = []
            for result in results:
                text = result.get("text", "")[:100]
                title = result.get("metadata", {}).get("title", text)
                if title and title not in suggestions:
                    suggestions.append(title)
            return suggestions[:MAX_SUGGESTIONS]
        except Exception as e:
            logger.error(f"Suggestions error: {e}")
            return []

    @staticmethod
    def create_suggestion_dropdown(
        choices: list[str],
    ) -> gr.Dropdown:
        """Create suggestion dropdown component.

        Args:
            choices: List of suggestion choices

        Returns:
            Gradio Dropdown component
        """
        if not choices:
            return gr.Dropdown(choices=[], visible=False)
        return gr.Dropdown(
            choices=choices,
            label="Suggestions",
            visible=True,
        )
