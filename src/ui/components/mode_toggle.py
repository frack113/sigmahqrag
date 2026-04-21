"""Mode toggle component."""

import gradio as gr


class ModeToggle:
    """Mode toggle component."""

    MODES = ["search", "coverage", "explain"]

    def __init__(self) -> None:
        """Initialize the mode toggle."""
        self.component = gr.Radio(
            choices=self.MODES,
            value="search",
            label="Mode",
        )

    def get_component(self) -> gr.Component:
        """Get the component."""
        return self.component
