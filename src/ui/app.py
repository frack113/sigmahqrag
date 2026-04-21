"""Gradio interface."""

import gradio as gr


def create_gradio_ui() -> gr.Interface:
    """Create the Gradio UI interface."""

    def greet(name: str) -> str:
        return f"Hello, {name}!"

    demo = gr.Interface(fn=greet, inputs="text", outputs="text")
    return demo
