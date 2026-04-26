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
    from src.api.routes.embeddings import router as embeddings_router
    from src.api.routes.admin_embedding import router as admin_embedding_router
    from src.api.routes.feedback import router as feedback_router
    from src.api.routes.admin_llm import router as admin_llm_router

    app = FastAPI(
        title="SigmaHQ RAG",
        version="0.1.0",
        description="Local RAG system for Sigma rules",
    )

    app.add_middleware(CorrelationIDMiddleware)

    app.include_router(auth_router)
    app.include_router(admin_router)
    app.include_router(documents_router)
    app.include_router(embeddings_router)
    app.include_router(admin_embedding_router)
    app.include_router(feedback_router)
    app.include_router(admin_llm_router)

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
    from src.ui.model_selector import scan_models

    chat = ChatInterface()
    mode = create_mode_toggle()

    with gr.Blocks(title="SigmaHQ RAG") as demo:
        gr.Markdown("# SigmaHQ RAG")
        gr.Markdown("Local RAG system for Sigma rules")
        gr.Markdown("[Chat](/gradio) | [Models](/models) | [Admin](/admin)")

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


def create_models_ui() -> gr.Blocks:
    """Create the Models management UI."""
    from src.core.services import ModelManager, EmbeddingManager

    async def search_models(query: str) -> list:
        """Search for models."""
        mm = ModelManager()
        results = await mm.search_models(query)
        return [(r.repo_id, f"{r.filename} ({r.size/1024/1024:.0f}MB)") for r in results]

    async def search_embeddings(query: str) -> list:
        """Search for embedding models."""
        em = EmbeddingManager()
        results = await em.search_models(query)
        return [(r.repo_id, f"{r.filename} ({r.size/1024/1024:.0f}MB)") for r in results]

    async def estimate_vram(repo_id: str) -> str:
        """Estimate VRAM for a model."""
        mm = ModelManager()
        try:
            result = await mm.estimate_vram(repo_id)
            if result.get("is_compatible"):
                return f"✅ Compatible - {result['estimated_vram_gb']}GB needed, {result['available_vram_gb']}GB available"
            else:
                return f"⚠️ Not compatible - {result['estimated_vram_gb']}GB needed, {result['available_vram_gb']}GB available"
        except Exception as e:
            return f"Error: {e}"

    async def download_model(repo_id: str) -> str:
        """Download a model."""
        mm = ModelManager()
        try:
            record = await mm.download_model(repo_id)
            return f"Downloaded to {record.local_path}"
        except Exception as e:
            return f"Error: {e}"

    async def list_installed() -> list:
        """List installed models."""
        mm = ModelManager()
        models = await mm.list_installed_models()
        return [(m.repo_id, f"{m.file_size/1024/1024:.0f}MB") for m in models]

    with gr.Blocks(title="Models") as demo:
        gr.Markdown("# Model Management")
        gr.Markdown("Download and manage LLM and embedding models")

        with gr.Tab("LLM Models"):
            gr.Markdown("### Download LLM Models")
            with gr.Row():
                llm_query = gr.Textbox(label="Search", placeholder="e.g., llama")
                dl_btn = gr.Button("Download")

            llm_results = gr.Dataframe(
                headers=["Repo ID", "Info"],
                label="Search Results",
            )

            with gr.Row():
                est_btn = gr.Button("Check VRAM")
                vram_output = gr.Textbox(label="VRAM Estimate")

            gr.Markdown("### Installed Models")
            installed_list = gr.Dataframe(
                headers=["Repo ID", "Size"],
                label="Installed Models",
            )
            installed_refresh = gr.Button("Refresh")
            
            def on_installed():
                import asyncio
                return asyncio.get_event_loop().run_until_complete(list_installed())
            
            installed_refresh.click(
                on_installed,
                outputs=[installed_list],
            )

        with gr.Tab("Embedding Models"):
            gr.Markdown("### Embedding Models")
            with gr.Row():
                emb_query = gr.Textbox(label="Search", placeholder="sentence-transformers")
                emb_dl_btn = gr.Button("Download")

            emb_results = gr.Dataframe(
                headers=["Repo ID", "Info"],
                label="Search Results",
            )

        dl_btn.click(
            search_models,
            inputs=[llm_query],
            outputs=[llm_results],
        )

        est_btn.click(
            estimate_vram,
            inputs=[llm_query],
            outputs=[vram_output],
        )

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
