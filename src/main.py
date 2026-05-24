"""Main application entry point."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from logging.handlers import RotatingFileHandler

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import URL

from src.api.routes.page_admin import router as admin_pages_router
from src.api.routes.page_chat import router as chat_page_router
from src.api.routes.page_data import router as data_page_router
from src.api.routes.page_duckdb import router as duckdb_page_router
from src.api.v1.admin import router as admin_v1_router
from src.api.v1.chat import router as chat_v1_router
from src.api.v1.config import router as config_v1_router
from src.api.v1.coverage import router as coverage_v1_router
from src.api.v1.dispatcher import router as dispatcher_v1_router
from src.api.v1.duckdb import router as duckdb_v1_router
from src.api.v1.documents import router as documents_v1_router
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
from src.back.llamacpp.auto_start import start_llamacpp, stop_llamacpp
from src.back.qdrant.auto_start import start_qdrant, stop_qdrant
from src.back.service_manager import shutdown_all_services
from src.worker.processor import TaskDispatcher
from src.worker.enums import WorkerName
from src.front import STATIC_DIR
from src.shared.exceptions import SigmaError
from src.shared import TEMP_DIR

logger = logging.getLogger(__name__)


def _parse_log_size(size_str: str) -> int:
    """Parse a human-readable size string (e.g. '5M', '10M', '1G') to bytes."""
    size_str = size_str.strip().upper()
    if size_str.endswith("G"):
        return int(float(size_str[:-1]) * 1024 * 1024 * 1024)
    if size_str.endswith("M"):
        return int(float(size_str[:-1]) * 1024 * 1024)
    if size_str.endswith("K"):
        return int(float(size_str[:-1]) * 1024)
    return int(size_str)


def _setup_logging(max_size: str = "10M", max_files: int = 5) -> None:
    """Setup logging to file with rotation."""
    from src.shared import LOGS_DIR

    log_file = LOGS_DIR / "sigmahqrag.log"

    handler = RotatingFileHandler(
        log_file, maxBytes=_parse_log_size(max_size), backupCount=max_files, encoding="utf-8"
    )
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)


def _clean_at_startup() -> None:
    """Clean temp, pid, and rotated log files at startup when clean_at_startup is enabled."""
    from src.shared import PID_DIR, LOGS_DIR

    for d in (TEMP_DIR, PID_DIR):
        if d.exists():
            for p in d.iterdir():
                try:
                    if p.is_file():
                        p.unlink()
                    elif p.is_dir():
                        import shutil

                        shutil.rmtree(p)
                except Exception as e:
                    logger.warning("Could not clean %s: %s", p, e)

    # Remove rotated log files (keep current sigmahqrag.log)
    if LOGS_DIR.exists():
        for p in LOGS_DIR.iterdir():
            if p.is_file() and p.name != "sigmahqrag.log":
                try:
                    p.unlink()
                except Exception as e:
                    logger.warning("Could not clean %s: %s", p, e)

    logger.info("Cleanup at startup: temp, pid, and rotated logs cleared.")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    dispatcher = None
    db = None
    try:
        db = DatabaseService()
        db.initialize()
        app.state.db = db

        from src.back.system_prompt import sync_prompts_from_files

        sync_prompts_from_files()

        from src.shared import Config

        Config.init_app()

        from src.shared import get_config

        config = get_config()
        _setup_logging(max_size=config.logging_log_max_size, max_files=config.logging_log_max_file)
        logger.info("=== Lifespan starting ===")
        logger.info("Database initialized.")
        logger.info("Config initialized.")

        if config.logging_clean_at_startup:
            _clean_at_startup()

        # Start the background task dispatcher in its own thread
        dispatcher = TaskDispatcher(poll_interval=1, max_workers=4)
        app.state.dispatcher = dispatcher
        dispatcher.start()
        logger.info("Dispatcher started in background thread.")

        # Queue model sync and repo sync as background worker tasks
        from src.shared import LLM_DIR, EMBEDDINGS_DIR

        logger.info("Queuing model sync as background worker...")
        if not dispatcher.ask_for_worker(
            WorkerName.MODEL_SYNC,
            llm_dir=str(LLM_DIR),
            embeddings_dir=str(EMBEDDINGS_DIR),
        ):
            logger.warning("Model sync not queued — worker is busy")
        else:
            logger.info("Model sync queued.")

        logger.info("Queuing repo sync as background worker...")
        if not dispatcher.ask_for_worker(WorkerName.LOCAL_REPO_SYNC):
            logger.warning("Repo sync not queued — worker is busy")
        else:
            logger.info("Repo sync queued.")

        _validate_services()
        logger.info("Services validated.")
        await start_llamacpp()
        logger.info("llama.cpp started.")
        await start_qdrant()
        logger.info("Qdrant started.")
        logger.info("=== Application startup complete ===")
    except BaseException as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise
    yield
    if dispatcher:
        dispatcher.stop()
        logger.info("Dispatcher stopped.")
    await stop_llamacpp()
    await shutdown_all_services()
    await stop_qdrant()
    if db:
        db.close()


def _validate_services() -> None:
    """Validate required services are configured."""
    from src.shared import get_config

    config = get_config()
    if not config.llama_base_url:
        logger.warning("LLM service not configured (llama_base_url missing)")
    if not config.qdrant_collection_name:
        logger.warning("Qdrant service not configured (qdrant_collection_name missing)")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="SigmaHQ RAG",
        version="0.1.0",
        description="Local RAG system for Sigma rules",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def csrf_protection(request: Request, call_next):
        if request.method in ("POST", "PUT", "DELETE", "PATCH"):
            origin = request.headers.get("origin", "")
            referer = request.headers.get("referer", "")
            if origin or referer:
                allowed = False
                for val in (origin, referer):
                    if not val:
                        continue
                    try:
                        parsed = URL(val)
                        if (
                            parsed.hostname in ("localhost", "127.0.0.1", "::1")
                            or parsed.scheme == "null"
                        ):
                            allowed = True
                            break
                    except Exception:
                        pass
                if not allowed:
                    return JSONResponse(
                        status_code=403, content={"error": "Cross-site request blocked"}
                    )
        return await call_next(request)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    app.include_router(admin_pages_router)
    app.include_router(admin_v1_router)
    app.include_router(duckdb_page_router)
    app.include_router(duckdb_v1_router)
    app.include_router(config_v1_router)
    app.include_router(coverage_v1_router)
    app.include_router(dispatcher_v1_router)
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
