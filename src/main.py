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
from src.api.routes.page_logs import router as logs_page_router
from src.api.v1.admin import router as admin_v1_router
from src.api.v1.admin_models import router as admin_models_router
from src.api.v1.chat import router as chat_v1_router
from src.api.v1.config import router as config_v1_router
from src.api.v1.coverage import router as coverage_v1_router
from src.api.v1.dispatcher import router as dispatcher_v1_router
from src.api.v1.documents import router as documents_v1_router
from src.api.v1.duckdb import router as duckdb_v1_router
from src.api.v1.embeddings import router as embeddings_v1_router
from src.api.v1.explain import router as explain_v1_router
from src.api.v1.feedback import router as feedback_v1_router
from src.api.v1.files import router as files_v1_router
from src.api.v1.github import router as github_v1_router
from src.api.v1.llamacpp import router as llama_router
from src.api.v1.logs import router as logs_v1_router
from src.api.v1.models_embedding import router as models_embedding_router
from src.api.v1.models_llm import router as models_llm_router
from src.api.v1.qdrant import router as qdrant_router
from src.api.v1.search import router as search_v1_router
from src.api.v1.spec import router as spec_v1_router
from src.api.v1.system_prompt import router as prompts_v1_router
from src.api.v1.translate import router as translate_v1_router
from src.application.service_manager import shutdown_all_services
from src.config.settings import TEMP_DIR
from src.front import STATIC_DIR
from src.infrastructure.database import DatabaseService
from src.infrastructure.llm.llamacpp.auto_start import start_llamacpp, stop_llamacpp
from src.infrastructure.vectorstore.auto_start import start_qdrant, stop_qdrant
from src.shared.exceptions import SigmaError
from src.worker.processor import TaskDispatcher

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


def _setup_logging(level: str = "INFO", max_size: str = "10M", max_files: int = 5) -> None:
    """Setup logging to file with rotation."""
    from src.config.settings import LOGS_DIR

    log_file = LOGS_DIR / "sigmahqrag.log"
    log_level = getattr(logging, level.upper(), logging.INFO)

    handler = RotatingFileHandler(
        log_file, maxBytes=_parse_log_size(max_size), backupCount=max_files, encoding="utf-8"
    )
    handler.setLevel(log_level)

    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    for noisy in ("httpx", "httpcore", "urllib3", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


async def _init_qdrant_collections() -> None:
    """Ensure all RAG collections exist with hybrid search enabled."""
    from src.infrastructure.vectorstore import QdrantVectorService

    for col in ("sigma_rules", "sigma_docs", "sigma_spec"):
        try:
            svc = QdrantVectorService(collection_name=col)
            await svc.create_collection(enable_hybrid=True)
        except Exception as e:
            logger.warning("Could not create Qdrant collection '%s': %s", col, e)


def _clean_at_startup() -> None:
    """Clean temp, pid, and log files at startup when clean_at_startup is enabled."""
    import shutil

    from src.config.settings import LOGS_DIR, PID_DIR

    for d in (TEMP_DIR, PID_DIR):
        if d.exists():
            for p in d.iterdir():
                try:
                    if p.is_file():
                        p.unlink()
                    elif p.is_dir():
                        shutil.rmtree(p)
                except Exception as e:
                    print(f"Could not clean {p}: {e}")

    # Clear all log files (they will be recreated by the handler)
    if LOGS_DIR.exists():
        for p in LOGS_DIR.iterdir():
            if p.is_file():
                try:
                    p.write_text("")
                except Exception as e:
                    print(f"Could not clear {p}: {e}")
        print("Cleanup at startup: all log files cleared.")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan handler."""
    dispatcher = None
    db = None
    try:
        db = DatabaseService()
        db.initialize()
        app.state.db = db

        from src.application.system_prompt import sync_prompts_from_files

        sync_prompts_from_files()

        from src.config.settings import Config, get_config

        Config.init_app()
        config = get_config()
        # Apply DuckDB overrides (replaces removed Config.apply_db_overrides)
        for key, attr in (
            ("backend.os", "os"),
            ("backend.gpu_type", "gpu_type"),
            ("llamacpp_version", "llamacpp_version"),
            ("qdrant_version", "qdrant_version"),
            ("qdrant_webui_version", "qdrant_webui_version"),
        ):
            val = db.get_config(key)
            if val is not None and isinstance(val, dict):
                val = val.get("value")
            if val is not None:
                current = getattr(config, attr, None)
                if isinstance(current, int) and isinstance(val, str):
                    try:
                        val = int(val)
                    except (ValueError, TypeError):
                        pass
                setattr(config, attr, val)
        logger.info("DuckDB config overrides applied.")

        if config.logging_clean_at_startup:
            _clean_at_startup()

        _setup_logging(
            level=config.logging_level,
            max_size=config.logging_log_max_size,
            max_files=config.logging_log_max_file,
        )
        logger.info("=== Lifespan starting ===")
        logger.info("Database initialized.")
        logger.info("Config initialized.")

        # Start the background task dispatcher in its own thread
        dispatcher = TaskDispatcher(poll_interval=1, max_workers=4)
        app.state.dispatcher = dispatcher
        dispatcher.start()
        logger.info("Dispatcher started in background thread.")

        _validate_services()
        logger.info("Services validated.")
        await start_llamacpp()
        logger.info("llama.cpp started.")
        await start_qdrant()
        logger.info("Qdrant started.")

        await _init_qdrant_collections()
        logger.info("Qdrant collections initialized.")

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
    from src.config.settings import get_config

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
    app.include_router(admin_models_router)
    app.include_router(duckdb_page_router)
    app.include_router(logs_page_router)
    app.include_router(duckdb_v1_router)
    app.include_router(config_v1_router)
    app.include_router(coverage_v1_router)
    app.include_router(dispatcher_v1_router)
    app.include_router(explain_v1_router)
    app.include_router(files_v1_router)
    app.include_router(github_v1_router)
    app.include_router(llama_router)
    app.include_router(logs_v1_router)
    app.include_router(models_llm_router)
    app.include_router(models_embedding_router)
    app.include_router(qdrant_router)
    app.include_router(search_v1_router)
    app.include_router(spec_v1_router)
    app.include_router(prompts_v1_router)
    app.include_router(translate_v1_router)
    app.include_router(chat_v1_router)
    app.include_router(chat_page_router)
    app.include_router(data_page_router)
    app.include_router(documents_v1_router)
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
