"""Results display component."""

from __future__ import annotations

from typing import Any

import gradio as gr


def create_results_panel() -> tuple[gr.List, gr.Markdown]:
    """Create split-pane results panel components.

    Returns:
        Tuple of (results_list, details_panel)
    """
    results_list = gr.List(
        label="Results",
        height=400,
    )
    details_panel = gr.Markdown(
        value="Select a result to view details",
        label="Details",
        height=400,
    )

    return results_list, details_panel


def create_results_list() -> gr.List:
    """Create results list component."""
    return gr.List(
        label="Results",
        height=400,
    )


def create_details_panel() -> gr.Markdown:
    """Create details panel component."""
    return gr.Markdown(
        value="Select a result to view details",
        label="Details",
        height=400,
    )


def format_result_item(result: dict[str, Any]) -> str:
    """Format a result for display in list.

    Args:
        result: Search result

    Returns:
        Formatted string for display
    """
    text = result.get("text", "")[:100]
    score = result.get("score", 0)
    citation = result.get("metadata", {}).get("file_path", "")
    if citation:
        return f"{text}... (score: {score:.2f}) [{citation}]"
    return f"{text}... (score: {score:.2f})"
