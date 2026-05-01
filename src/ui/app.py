"""Gradio interface with split-pane search."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import gradio as gr

from src.rag.search import SearchEngine
from src.ui.chat import SearchInterface
from src.ui.components.details_panel import DetailsPanel

logger = logging.getLogger(__name__)

MAX_RESULTS = 10
SEARCH_TIMEOUT = 3.0


def create_gradio_ui() -> gr.Blocks:
    """Create the Gradio UI with split-pane layout."""

    search_engine = SearchEngine()
    search_interface = SearchInterface(search_engine)

    results_state = gr.State(value=[])

    def on_search(
        query: str,
        results: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], str, str]:
        """Handle search submit."""
        if not query or not query.strip():
            return [], DetailsPanel.format_empty_state(), gr.update(visible=False)

        card_htmls, details = asyncio.get_event_loop().run_until_complete(
            search_interface.handle_search(query)
        )

        loading = gr.update(visible=False)
        return card_htmls, details, loading

    def on_suggestions(
        query: str,
    ) -> tuple[list[str], str]:
        """Handle live suggestions with debounce."""
        if not query or len(query.strip()) < 2:
            return [], gr.update(visible=False)

        suggestions = asyncio.get_event_loop().run_until_complete(
            search_interface.get_suggestions(query)
        )

        if suggestions:
            return suggestions, gr.update(visible=True)
        return [], gr.update(visible=False)

    def on_select_result(
        evt: gr.SelectData,
        results: list[dict[str, Any]],
    ) -> str:
        """Handle result selection."""
        return search_interface.handle_result_click(evt.index, results)

    with gr.Blocks(
        title="Sigma HQ RAG",
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="gray",
        ),
    ) as demo:
        gr.Markdown(
            "# Sigma HQ RAG\nSearch Sigma rules by intention"
        )

        with gr.Row():
            with gr.Column(scale=4):
                search_input = gr.Textbox(
                    label="Recherche",
                    placeholder="Entrez votre requête (ex: détection de trafic suspect)",
                    lines=1,
                )
                with gr.Row():
                    search_btn = gr.Button("🔍 Rechercher", variant="primary")
                    clear_btn = gr.Button("Effacer")

            with gr.Column(scale=1):
                gr.Radio(
                    choices=["search", "coverage", "explain"],
                    value="search",
                    label="Mode",
                )

        with gr.Row(equal_height=False):
            with gr.Column(scale=4):
                loading_msg = gr.Markdown(
                    "Recherche en cours...",
                    visible=False,
                )
                results_list = gr.List(
                    [],
                    label="Résultats",
                    height=400,
                )

            with gr.Column(scale=6):
                details = gr.Markdown(
                    "Sélectionnez un résultat pour voir les détails",
                    label="Détails",
                )

        search_btn.click(
            on_search,
            inputs=[search_input, results_state],
            outputs=[results_state, details, loading_msg],
        )

        search_input.submit(
            on_search,
            inputs=[search_input, results_state],
            outputs=[results_state, details, loading_msg],
        )

        results_list.select(
            on_select_result,
            inputs=[results_state],
            outputs=[details],
        )

        def clear_search() -> tuple[list, str, str]:
            """Clear search state."""
            return [], DetailsPanel.format_empty_state(), ""

        clear_btn.click(
            clear_search,
            outputs=[results_state, details, search_input],
        )

    return demo
