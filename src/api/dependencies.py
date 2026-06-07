"""FastAPI dependencies."""

import logging
from typing import Any, cast

from fastapi import Request
from fastapi.responses import JSONResponse

from src.application.models import EmbeddingManager
from src.application.models.registry import UnifiedRegistry
from src.infrastructure.database.service import DatabaseService
from src.worker.processor import TaskDispatcher


def safe_error_response(
    status_code: int,
    public_message: str,
    exc: Exception,
    logger: logging.Logger,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    """Return a safe error response — logs the real error, returns a sanitized message."""
    logger.error(f"{public_message}: {exc}", exc_info=True)
    content: dict[str, Any] = {"error": public_message}
    if details:
        content["details"] = details
    return JSONResponse(status_code=status_code, content=content)


_embedding_manager_instance: EmbeddingManager | None = None


def get_database_service() -> DatabaseService:
    return DatabaseService.get_instance()


def get_dispatcher(req: Request) -> TaskDispatcher:
    dispatcher = getattr(req.app.state, "dispatcher", None)
    if dispatcher is None:
        raise RuntimeError("TaskDispatcher not available")
    return cast(TaskDispatcher, dispatcher)


def get_embedding_manager() -> EmbeddingManager:
    global _embedding_manager_instance
    if _embedding_manager_instance is None:
        _embedding_manager_instance = EmbeddingManager()
    return _embedding_manager_instance


def get_unified_registry() -> UnifiedRegistry:
    return UnifiedRegistry.get_instance()
