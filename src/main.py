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
        """Root endpoint - redirect to admin dashboard."""
        return HTMLResponse(
            content="<html><head><meta http-equiv='refresh' content='0;url=/admin'></head></html>"
        )

    return app


if __name__ == "__main__":
    import uvicorn

    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=7860)
