"""SigmaHQ RAG - FastAPI + Gradio application."""

import logging
import uuid
from contextvars import ContextVar

import gradio as gr
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from src.errors import (
    ModelNotFoundError,
    ServiceUnavailableError,
    SigmaError,
    ValidationError,
)

logger = logging.getLogger(__name__)

correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def _validate_services() -> None:
    """Validate external services at startup (LLM, Qdrant)."""
    import httpx

    from src.config import load_config

    config = load_config()

    # Check LLM service
    llm_config = config.get("services", {}).get("llama", {})
    llm_url = llm_config.get("base_url", "http://localhost:11434")

    try:
        response = httpx.get(f"{llm_url}/api/tags", timeout=5.0)
        if response.status_code == 200:
            logger.info(f"LLM service available at {llm_url}")
        else:
            logger.warning(f"LLM service returned status {response.status_code} at {llm_url}")
    except httpx.ConnectError:
        logger.warning(f"LLM service NOT available at {llm_url} - chat features will use fallback")
    except Exception as e:
        logger.warning(f"LLM service check failed: {e}")

    # Check Qdrant collection
    qdrant_config = config.get("services", {}).get("qdrant", {})
    qdrant_host = qdrant_config.get("host", "localhost")
    qdrant_port = qdrant_config.get("port", 6333)
    collection = qdrant_config.get("collection_name", "sigma_rules")

    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(host=qdrant_host, port=qdrant_port, timeout=5.0)
        collections = client.get_collections().collections
        if any(c.name == collection for c in collections):
            logger.info(f"Qdrant collection '{collection}' exists")
        else:
            logger.warning(f"Qdrant collection '{collection}' NOT found - search will return empty")
    except Exception as e:
        logger.warning(f"Qdrant check failed: {e} - search features may be unavailable")


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
    from src.api.routes.admin_backend import router as admin_backend_router
    from src.api.routes.admin_embedding import router as admin_embedding_router
    from src.api.routes.admin_github import router as admin_github_router
    from src.api.routes.admin_llm import router as admin_llm_router
    from src.api.routes.admin_pages import router as admin_pages_router
    from src.api.routes.admin_prompts import router as admin_prompts_router
    from src.api.routes.admin_service import router as admin_router
    from src.api.routes.chat import router as chat_router
    from src.api.routes.documents import router as documents_router
    from src.api.routes.embeddings import router as embeddings_router
    from src.api.routes.feedback import router as feedback_router
    from src.api.v1.admin import router as admin_v1_router

    # Startup validation
    _validate_services()

    app = FastAPI(
        title="SigmaHQ RAG",
        version="0.1.0",
        description="Local RAG system for Sigma rules",
    )

    app.add_middleware(CorrelationIDMiddleware)
    app.mount("/static", StaticFiles(directory="src/static"), name="static")

    app.include_router(admin_router)
    app.include_router(documents_router)
    app.include_router(embeddings_router)
    app.include_router(admin_embedding_router)
    app.include_router(feedback_router)
    app.include_router(admin_llm_router)
    app.include_router(admin_backend_router)
    app.include_router(admin_prompts_router)
    app.include_router(admin_github_router)
    app.include_router(admin_v1_router)
    app.include_router(admin_pages_router)
    app.include_router(chat_router)

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
    async def model_not_found_handler(request: Request, exc: ModelNotFoundError) -> JSONResponse:
        """Handle ModelNotFoundError exceptions."""
        _log_error_with_context(request, exc)
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict(),
        )

    @app.exception_handler(ValidationError)
    async def validation_error_handler(request: Request, exc: ValidationError) -> JSONResponse:
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
    from src.core.services import ModelManager

    async def list_files(repo_id: str) -> list:
        """List GGUF files for a repo."""
        if not repo_id:
            return []
        from src.core.types import HFRepo

        mm = ModelManager()
        try:
            files = mm.download_service.list_gguf_files(HFRepo.from_string(repo_id))
            return [f["filename"] for f in files]
        except Exception:
            return []

    async def list_installed() -> list:
        """List installed models."""
        mm = ModelManager()
        models = await mm.list_installed_models()
        result = []
        for m in models:
            for fn, f in m.files.items():
                size_mb = f.file_size / 1024 / 1024
                result.append((f"{m.repo_id}/{fn}", f"{size_mb:.0f}MB"))
        return result

    async def delete_model(repo_id: str, filename: str | None = None) -> str:
        """Delete a model."""
        mm = ModelManager()
        try:
            await mm.delete_model(repo_id, filename)
            return "Deleted successfully"
        except Exception as e:
            return f"Error: {e}"

    with gr.Blocks(title="Models") as demo:
        gr.Markdown("# Model Management")
        gr.Markdown("Download and manage LLM and embedding models")

        with gr.Tab("LLM Models"):
            gr.Markdown("### Download LLM Model")
            with gr.Row():
                llm_repo = gr.Textbox(
                    label="Repo ID",
                    placeholder="e.g., leliuga/gemma-2b-it-GGUF",
                    scale=2,
                )
                search_btn = gr.Button("Search Files", scale=1)

            file_list = gr.Dropdown(
                label="Select Quantization",
                choices=[],
                interactive=True,
            )

            with gr.Row():
                dl_btn = gr.Button("Download", variant="primary")

            dl_output = gr.Textbox(label="Status")

            search_btn.click(
                list_files,
                inputs=[llm_repo],
                outputs=[file_list],
            )

            def on_download_click(repo_id: str, selected_file: str):
                if not repo_id or not selected_file:
                    return "Please enter repo ID and select a file"

                async def do_download():
                    mm = ModelManager()
                    return await mm.download_model(repo_id, selected_file)

                try:
                    import asyncio

                    record = asyncio.get_event_loop().run_until_complete(do_download())
                    return f"Downloaded: {record.local_path}"
                except Exception as e:
                    return f"Error: {e}"

            dl_btn.click(
                on_download_click,
                inputs=[llm_repo, file_list],
                outputs=[dl_output],
            )

            gr.Markdown("### Installed Models")
            installed_list = gr.Dataframe(
                headers=["Model", "Size"],
                label="Installed Models",
            )
            with gr.Row():
                installed_refresh = gr.Button("Refresh")
                delete_btn = gr.Button("Delete Selected", variant="stop")
            delete_output = gr.Textbox(label="Delete Status")

            def on_installed():
                import asyncio

                return asyncio.get_event_loop().run_until_complete(list_installed())

            installed_refresh.click(
                on_installed,
                outputs=[installed_list],
            )

            def on_delete(selected):
                if not selected:
                    return "No model selected"
                import asyncio

                return asyncio.get_event_loop().run_until_complete(
                    delete_model(selected[0], selected[0].split("/")[-1])
                )

            delete_btn.click(
                on_delete,
                inputs=[installed_list],
                outputs=[delete_output],
            )

        with gr.Tab("Embedding Models"):
            gr.Markdown("### Embedding Models")
            gr.Markdown("*Coming soon*")

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
