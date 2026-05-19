"""Main application entry point."""

import asyncio
import logging
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from src.api.routes.page_admin import router as admin_pages_router
from src.api.routes.page_chat import router as chat_page_router
from src.api.routes.page_data import router as data_page_router
from src.api.routes.page_duckdb import router as duckdb_page_router
from src.api.v1.admin import router as admin_v1_router
from src.api.v1.chat import router as chat_v1_router
from src.api.v1.config import router as config_v1_router
from src.api.v1.coverage import router as coverage_v1_router
from src.api.v1.documents import router as documents_v1_router
from src.api.v1.duckdb import router as duckdb_v1_router
from src.api.v1.embedding_config import router as embedding_config_v1_router
from src.api.v1.embeddings import router as embeddings_v1_router
from src.api.v1.explain import router as explain_v1_router
from src.api.v1.feedback import router as feedback_v1_router
from src.api.v1.files import router as files_v1_router
from src.api.v1.github import router as github_v1_router
from src.api.v1.llamacpp import router as llama_router
from src.api.v1.logs import router as logs_v1_router
from src.api.v1.models import router as models_v1_router
from src.api.v1.qdrant import router as qdrant_router
from src.api.v1.search import router as search_v1_router
from src.api.v1.system_prompt import router as prompts_v1_router
from src.back.database import DatabaseService
from src.back.qdrant.auto_start import start_qdrant, stop_qdrant
from src.back.service_manager import shutdown_all_services
from src.back.worker.processor import TaskDispatcher
from src.shared.exceptions import SigmaError

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    """Setup logging to file with rotation."""
    from src.shared import LOGS_DIR

    log_file = LOGS_DIR / "sigmahqrag.log"

    handler = RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def _is_db_empty(db: DatabaseService) -> bool:
    for table in (
        "config",
        "embedding_config",
        "system_prompts",
        "models",
        "doc_sigma_ref",
        "git_metadata",
        "git_selected_dirs",
    ):
        if db.get_table_count(table) > 0:
            return False
    return True


def _check_old_data_files() -> list[str]:
    old_paths = [
        Path("data/embedding.toml"),
        Path("data/system_prompt.toml"),
        Path("data/models/registry.json"),
        Path("data/models/embeddings/embeddings_registry.json"),
        Path("data/documents/sigmaref/registry.json"),
    ]
    return [str(p) for p in old_paths if p.exists()]


@asynccontextmanager
async def lifespan(app: FastAPI) -> None:
    """Application lifespan handler."""
    _setup_logging()
    from src.shared import Config

    Config.init_app()

    db = DatabaseService()
    db.initialize()
    app.state.db = db

    old_files = _check_old_data_files()
    if old_files and _is_db_empty(db):
        logger.warning(
            "DuckDB is empty but old data files exist (%d found). "
            "Run 'uv run python scripts/migrate_to_duckdb.py' to migrate data.",
            len(old_files),
        )

    db.reset_stale_workers()

    # Initialize worker states so the frontend always sees all workers
    db.init_worker_states(list(TaskDispatcher._WORKER_TYPES.keys()))

    # Sync filesystem repos into git_metadata if missing
    from src.back.github.git import list_repos, get_metadata, save_metadata

    for repo in list_repos():
        repo_key = f"{repo['org']}/{repo['name']}"
        if get_metadata(repo["org"], repo["name"]) is None:
            logger.info("Syncing filesystem repo %s into git_metadata", repo_key)
            save_metadata(
                repo["org"],
                repo["name"],
                {
                    "org": repo["org"],
                    "name": repo["name"],
                    "url": repo.get("remote_url", ""),
                    "branch": repo.get("branch", "main"),
                    "status": "synced",
                },
            )

    # Sync filesystem models into DuckDB models table
    from src.api.dependencies import get_unified_registry
    from src.shared import LLM_DIR, EMBEDDINGS_DIR

    reg = get_unified_registry()
    reg.sync_llm_folder(LLM_DIR)
    reg.sync_embeddings_folder(EMBEDDINGS_DIR)

    # Start the background task dispatcher
    dispatcher = TaskDispatcher(poll_interval=5)
    app.state.dispatcher = dispatcher
    dispatcher_task = asyncio.create_task(dispatcher.run())

    _validate_services()
    await start_qdrant()
    yield
    dispatcher.stop()
    dispatcher_task.cancel()
    await shutdown_all_services()
    await stop_qdrant()
    db.close()


def _validate_services() -> None:
    """Validate required services are configured."""
    from src.shared import get_config

    config = get_config()
    if not config.llama_base_url:
        logger.critical("LLM service not configured")
        raise SystemExit(1)
    if not config.qdrant_collection_name:
        logger.critical("Qdrant service not configured")
        raise SystemExit(1)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="SigmaHQ RAG",
        version="0.1.0",
        description="Local RAG system for Sigma rules",
        lifespan=lifespan,
    )

    static_dir = str(Path(__file__).parent / "front" / "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    app.include_router(admin_pages_router)
    app.include_router(admin_v1_router)
    app.include_router(duckdb_page_router)
    app.include_router(duckdb_v1_router)
    app.include_router(config_v1_router)
    app.include_router(coverage_v1_router)
    app.include_router(explain_v1_router)
    app.include_router(files_v1_router)
    app.include_router(github_v1_router)
    app.include_router(llama_router)
    app.include_router(logs_v1_router)
    app.include_router(models_v1_router)
    app.include_router(qdrant_router)
    app.include_router(search_v1_router)
    app.include_router(prompts_v1_router)
    app.include_router(chat_v1_router)
    app.include_router(chat_page_router)
    app.include_router(data_page_router)
    app.include_router(documents_v1_router)
    app.include_router(embedding_config_v1_router)
    app.include_router(embeddings_v1_router)
    app.include_router(feedback_v1_router)

    @app.exception_handler(SigmaError)
    async def sigma_error_handler(request: Request, exc: SigmaError) -> JSONResponse:
        """Global handler for SigmaError exceptions."""
        logger.error(f"SigmaError ({exc.code}): {exc.message}")
        return JSONResponse(
            status_code=exc.http_status,
            content=exc.to_dict(),
        )

    return app


app = create_app()
