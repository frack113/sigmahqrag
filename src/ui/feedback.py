"""Feedback widget for Gradio UI."""

import logging

import gradio as gr

logger = logging.getLogger(__name__)

_feedback_submitted = False


def create_feedback_widget() -> tuple[gr.Column, gr.Button, gr.Button]:
    """Create feedback Yes/No buttons.

    Returns:
        Tuple of (container, yes_button, no_button)
    """
    with gr.Column(visible=False) as feedback_container:
        gr.Markdown("### Was this helpful?")
        with gr.Row():
            yes_btn = gr.Button("✅ Yes", variant="primary")
            no_btn = gr.Button("❌ No", variant="secondary")

    return feedback_container, yes_btn, no_btn


def format_feedback_submitted() -> str:
    """Format feedback confirmation message."""
    return "Thank you for your feedback!"


async def submit_feedback_api(query: str, helpful: bool) -> bool:
    """Submit feedback to API.

    Args:
        query: The search query
        helpful: Whether the results were helpful

    Returns:
        True if successful
    """
    try:
        import httpx

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:7860/api/feedback",
                json={"query": query, "helpful": helpful},
                timeout=5.0,
            )
            return response.status_code == 201
    except Exception as e:
        logger.error(f"Feedback submission error: {e}")
        return False