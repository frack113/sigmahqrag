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
    from sigmahqrag.api.routes.admin import router as admin_router

    app = FastAPI(
        title="SigmaHQ RAG",
        version="0.1.0",
        description="Local RAG system for Sigma rules",
    )

    app.include_router(admin_router)

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
    from sigmahqrag.ui.chat import ChatInterface
    from sigmahqrag.ui.mode import create_mode_toggle

    chat = ChatInterface()
    mode = create_mode_toggle()

    with gr.Blocks(title="SigmaHQ RAG") as demo:
        gr.Markdown("# SigmaHQ RAG")
        gr.Markdown("Local RAG system for Sigma rules")

        with gr.Row():
            mode.render()

        chatbot = gr.Chatbot(label="Chat History", height=500)
        msg = gr.Textbox(
            label="Message",
            placeholder="Ask about Sigma rules...",
            lines=2,
        )
        clear = gr.Button("Clear")

        async def respond(
            message: str, history: list[list[str]], mode: str
        ) -> tuple[str, list[list[str]]]:
            return await chat.chat(message, history, mode)

        msg.submit(
            fn=respond,
            inputs=[msg, chatbot, mode],
            outputs=[msg, chatbot],
        )
        clear.click(lambda: (None, []), outputs=[msg, chatbot])

    return demo  # type: ignore[no-any-return]


def create_admin_ui() -> gr.Blocks:
    """Create the admin Gradio UI interface."""
    from sigmahqrag.ui.admin import create_admin_ui as make_admin_ui

    return make_admin_ui()


app = create_app()
gradio_ui = create_gradio_ui()
admin_ui = create_admin_ui()
app = gr.mount_gradio_app(app, gradio_ui, "/gradio")
app = gr.mount_gradio_app(app, admin_ui, "/admin")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
