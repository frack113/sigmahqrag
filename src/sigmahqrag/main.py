"""SigmaHQ RAG - FastAPI + Gradio application."""

import logging

import gradio as gr
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from src.errors import (
    ModelNotFoundError,
    ServiceUnavailableError,
    SigmaError,
    ValidationError,
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="SigmaHQ RAG",
        version="0.1.0",
        description="Local RAG system for Sigma rules",
    )

    @app.exception_handler(SigmaError)
    async def sigma_error_handler(request: Request, exc: SigmaError) -> JSONResponse:
        """Handle SigmaError exceptions."""
        logger.error(f"Sigma error: {exc.message}")
        return JSONResponse(
            status_code=500,
            content=exc.to_dict(),
        )

    @app.exception_handler(ServiceUnavailableError)
    async def service_unavailable_handler(
        request: Request, exc: ServiceUnavailableError
    ) -> JSONResponse:
        """Handle ServiceUnavailableError exceptions."""
        logger.error(f"Service unavailable: {exc.message}")
        return JSONResponse(
            status_code=503,
            content=exc.to_dict(),
        )

    @app.exception_handler(ModelNotFoundError)
    async def model_not_found_handler(
        request: Request, exc: ModelNotFoundError
    ) -> JSONResponse:
        """Handle ModelNotFoundError exceptions."""
        logger.error(f"Model not found: {exc.message}")
        return JSONResponse(
            status_code=404,
            content=exc.to_dict(),
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        """Handle ValidationError exceptions."""
        logger.error(f"Validation error: {exc.message}")
        return JSONResponse(
            status_code=422,
            content=exc.to_dict(),
        )

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.get("/")
    async def root() -> HTMLResponse:
        """Root endpoint - redirect to Gradio UI."""
        return HTMLResponse(
            content="<html><head><meta http-equiv='refresh' content='0;url=/gradio'></head></html>"
        )

    return app


def create_gradio_ui() -> gr.Blocks:
    """Create the Gradio UI interface."""

    def greet(name: str) -> str:
        return f"Hello, {name}!"

    with gr.Blocks(title="SigmaHQ RAG") as demo:
        gr.Markdown("# SigmaHQ RAG")
        gr.Markdown("Local RAG system for Sigma rules")
        with gr.Row():
            with gr.Column():
                input_text = gr.Textbox(label="Input")
            with gr.Column():
                output_text = gr.Textbox(label="Output")
        submit_btn = gr.Button("Submit")
        submit_btn.click(fn=greet, inputs=input_text, outputs=output_text)

    return demo  # type: ignore[no-any-return]


app = create_app()
gradio_ui = create_gradio_ui()
app = gr.mount_gradio_app(app, gradio_ui, "/gradio")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7860)
