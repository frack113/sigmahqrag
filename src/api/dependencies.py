"""FastAPI dependencies."""

from typing import cast

from fastapi import Request

from src.back.database.service import DatabaseService
from src.back.models import EmbeddingManager
from src.back.models.registry import UnifiedRegistry
from src.worker.processor import TaskDispatcher

_embedding_manager_instance: EmbeddingManager | None = None
_unified_registry_instance: UnifiedRegistry | None = None


def get_database_service() -> DatabaseService:
    return DatabaseService.get_instance()


def get_dispatcher(req: Request) -> TaskDispatcher:
    if not hasattr(req.app.state, "dispatcher"):
        raise RuntimeError("TaskDispatcher not available")
    return cast(TaskDispatcher, req.app.state.dispatcher)


def get_embedding_manager() -> EmbeddingManager:
    global _embedding_manager_instance
    if _embedding_manager_instance is None:
        _embedding_manager_instance = EmbeddingManager()
    return _embedding_manager_instance


def get_unified_registry() -> UnifiedRegistry:
    return UnifiedRegistry.get_instance()
