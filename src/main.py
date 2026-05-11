"""Main application entry point."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.api.routes.page_admin import router as admin_pages_router
from src.api.routes.page_chat import router as chat_page_router
from src.api.routes.page_data import router as data_page_router
from src.api.v1.admin import router as admin_v1_router
from src.api.v1.chat import router as chat_v1_router
from src.api.v1.config import router as config_v1_router
from src.api.v1.coverage import router as coverage_v1_router
from src.api.v1.documents import router as documents_v1_router
from src.api.v1.embeddings import router as embeddings_v1_router
from src.api.v1.explain import router as explain_v1_router
from src.api.v1.feedback import router as feedback_v1_router
from src.api.v1.github import router as github_v1_router
from src.api.v1.llamacpp import router as llama_router
from src.api.v1.logs import router as logs_v1_router
from src.api.v1.model import router as model_v1_router
from src.api.v1.qdrant import router as qdrant_router
from src.api.v1.search import router as search_v1_router
from src.api.v1.system_prompt import router as prompts_v1_router
from src.back.service_manager import get_subprocess_manager, shutdown_all_services


def _setup_logging() -> None:
    """Setup logging to file."""
    log_file = Path("data/logs/sigmahqrag.log")
    log_file.parent.mkdir(parents=True, exist_ok=True)

    handler = logging.FileHandler(log_file, encoding="utf-8")
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def _get_subprocess_manager():
    """Get or create the global subprocess manager."""
    return get_subprocess_manager()


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Application lifespan handler."""
    _setup_logging()
    from src.shared import Config

    Config.init_app()
    _validate_services()
    yield
    await shutdown_all_services()


def _validate_services() -> None:
    """Validate required services are configured."""
    from src.shared import get_config

    config = get_config()
    if not config.llama_base_url:
        raise ValueError("LLM service not configured")
    if not config.qdrant_collection_name:
        raise ValueError("Qdrant service not configured")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="SigmaHQ RAG",
        version="0.1.0",
        description="Local RAG system for Sigma rules",
    )

    app.mount("/static", StaticFiles(directory="src/front/static"), name="static")

    app.include_router(admin_pages_router)
    app.include_router(admin_v1_router)
    app.include_router(config_v1_router)
    app.include_router(coverage_v1_router)
    app.include_router(explain_v1_router)
    app.include_router(search_v1_router)
    app.include_router(github_v1_router)
    app.include_router(llama_router)
    app.include_router(logs_v1_router)
    app.include_router(qdrant_router)
    app.include_router(model_v1_router)
    app.include_router(chat_page_router)
    app.include_router(data_page_router)
    app.include_router(chat_v1_router)
    app.include_router(documents_v1_router)
    app.include_router(embeddings_v1_router)
    app.include_router(feedback_v1_router)
    app.include_router(prompts_v1_router)

    return app


app = create_app()
