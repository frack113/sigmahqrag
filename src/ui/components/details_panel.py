"""Details panel component."""

import gradio as gr


class DetailsPanel:
    """Details panel component."""

    def __init__(self) -> None:
        """Initialize the details panel."""
        self.component = gr.Markdown()

    def get_component(self) -> gr.Component:
        """Get the component."""
        return self.component
