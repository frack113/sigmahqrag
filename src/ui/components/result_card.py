"""Result card component."""

import gradio as gr


class ResultCard:
    """Result card component."""

    def __init__(self) -> None:
        """Initialize the result card."""
        self.component = gr.JSON(label="Result")

    def get_component(self) -> gr.Component:
        """Get the component."""
        return self.component
