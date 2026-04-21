"""Mode toggle component."""

from __future__ import annotations

from enum import StrEnum

import gradio as gr


class ChatMode(StrEnum):
    """Chat modes."""

    SEARCH = "search"
    COVERAGE = "coverage"
    EXPLAIN = "explain"


def create_mode_toggle() -> gr.Radio:
    """Create mode toggle component."""
    return gr.Radio(
        choices=[ChatMode.SEARCH, ChatMode.COVERAGE, ChatMode.EXPLAIN],
        value=ChatMode.SEARCH,
        label="Mode",
    )
