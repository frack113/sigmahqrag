"""Search bar component."""

import gradio as gr


class SearchBar:
    """Search bar component."""

    def __init__(self) -> None:
        """Initialize the search bar."""
        self.component = gr.Textbox(
            label="Search",
            placeholder="Enter your query...",
        )

    def get_component(self) -> gr.Component:
        """Get the component."""
        return self.component
