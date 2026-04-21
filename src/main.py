"""FastAPI + Gradio mount entry point."""

import gradio as gr
from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="SigmaHQ RAG", version="0.1.0")
    return app


def create_gradio_ui() -> gr.Interface:
    """Create the Gradio UI interface."""
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    demo = gr.Interface(fn=greet, inputs="text", outputs="text")
    return demo


app = create_app()
gradio_app = create_gradio_ui()
app.mount("/gradio", gradio_app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
