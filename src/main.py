"""SigmaHQ RAG - FastAPI + Gradio application."""

import logging
import uuid
from contextvars import ContextVar

import gradio as gr
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from src.errors import (
    ModelNotFoundError,
    ServiceUnavailableError,
    SigmaError,
    ValidationError,
)

logger = logging.getLogger(__name__)

correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to add correlation ID to requests."""

    async def dispatch(self, request: Request, call_next):
        """Process request and add correlation ID."""
        correlation_id = request.headers.get("X-Correlation-ID")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        correlation_id_var.set(correlation_id)
        request.state.correlation_id = correlation_id

        response = await call_next(request)
        response.headers["X-Correlation-ID"] = correlation_id

        return response


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    from src.api.routes.admin import router as admin_router
    from src.api.routes.auth import router as auth_router
    from src.api.routes.documents import router as documents_router
    from src.api.routes.feedback import router as feedback_router

    app = FastAPI(
        title="SigmaHQ RAG",
        version="0.1.0",
        description="Local RAG system for Sigma rules",
    )

    app.add_middleware(CorrelationIDMiddleware)

    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(documents_router)
    app.include_router(feedback_router)

    @app.exception_handler(SigmaError)
    async def sigma_error_handler(request: Request, exc: SigmaError) -> JSONResponse:
        """Handle SigmaError exceptions."""
        _log_error_with_context(request, exc)
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict(),
        )

    @app.exception_handler(ServiceUnavailableError)
    async def service_unavailable_handler(
        request: Request, exc: ServiceUnavailableError
    ) -> JSONResponse:
        """Handle ServiceUnavailableError exceptions."""
        _log_error_with_context(request, exc)
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict(),
        )

    @app.exception_handler(ModelNotFoundError)
    async def model_not_found_handler(
        request: Request, exc: ModelNotFoundError
    ) -> JSONResponse:
        """Handle ModelNotFoundError exceptions."""
        _log_error_with_context(request, exc)
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict(),
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(
        request: Request, exc: ValidationError
    ) -> JSONResponse:
        """Handle ValidationError exceptions."""
        _log_error_with_context(request, exc)
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """Handle uncaught exceptions - returns 500 with clean message."""
        logger.exception(
            f"Unhandled exception: {exc}",
            extra={
                "request_method": request.method,
                "request_path": request.url.path,
                "request_query_params": str(request.query_params),
                "correlation_id": getattr(request.state, "correlation_id", None),
            },
        )
        return JSONResponse(
            status_code=500,
            content={
                "code": "INTERNAL_ERROR",
                "message": "An internal error occurred",
                "details": {},
            },
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


def _log_error_with_context(request: Request, exc: SigmaError) -> None:
    """Log error with request context."""
    logger.error(
        f"{exc.code}: {exc.message}",
        extra={
            "request_method": request.method,
            "request_path": request.url.path,
            "request_query_params": str(request.query_params),
            "correlation_id": getattr(request.state, "correlation_id", None),
            "error_details": exc.details,
        },
    )


def create_gradio_ui() -> gr.Blocks:
    """Create the Gradio UI interface."""
    from src.ui.chat import ChatInterface
    from src.ui.mode import create_mode_toggle

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
    from src.ui.admin import create_admin_ui as make_admin_ui

    return make_admin_ui()


app = create_app()
gradio_ui = create_gradio_ui()
admin_ui = create_admin_ui()
app = gr.mount_gradio_app(app, gradio_ui, "/gradio")
app = gr.mount_gradio_app(app, admin_ui, "/admin")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
