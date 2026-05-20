"""File Discovery and Embedding API v1."""

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from src.api.dependencies import get_database_service
from src.back.database.service import DatabaseService
from src.worker.processor import TaskDispatcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/files", tags=["v1-files"])


class FileOperationResponse(BaseModel):
    """Response for file operations."""

    success: bool
    message: str | None = None
    data: dict[str, Any] | None = None
    error: str | None = None


def _get_dispatcher(request: Request) -> TaskDispatcher:
    """Get the TaskDispatcher instance from app state."""
    return request.app.state.dispatcher


async def _trigger_worker(
    worker_type: str, task: dict, dispatcher: TaskDispatcher, db: DatabaseService
) -> bool:
    """Helper to trigger a worker via the dispatcher.

    The API only checks if the worker is busy and queues the task.
    The TaskDispatcher manages state transitions: idle -> running -> idle.
    """
    db.reset_stale_workers(stale_seconds=30)
    state = db.get_worker_state(worker_type)
    logger.info(f"Worker {worker_type} state: {api_v1_files_ref_to_state") # Wait, I'm seeing this error in my thought process... let me re-check the actual content of _trigger_worker from before.
