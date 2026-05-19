"""File Discovery and Embedding API v1."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.back.database.service import DatabaseService
from src.back.worker.processor import TaskDispatcher

router = APIRouter(prefix="/api/v1/files", tags=["v1-files"])


class FileOperationResponse(BaseModel):
    """Response for file operations."""

    success: bool
    message: str | None = None
    data: dict[str, Any] | None = None
    error: str | None = None


def _get_dispatcher() -> TaskDispatcher:
    """Get the TaskDispatcher instance from app state."""
    from src.main import app
    return app.state.dispatcher


async def _trigger_worker(worker_type: str, task: dict, dispatcher: TaskDispatcher) -> bool:
    """Helper to trigger a worker via the dispatcher."""
    db = DatabaseService.get_instance()
    if db.is_worker_busy(worker_type):
        return False

    task_id = str(uuid.uuid4())
    task["task_id"] = task_id
    db.upsert_worker_state(
        worker_type=worker_type,
        status="running",
        current_task_id=task_id,
    )
    
    await dispatcher.queue_task(worker_type, task)
    return True


@router.post("/list", response_model=FileOperationResponse)
async def file_list(dispatcher: TaskDispatcher = Depends(_get_dispatcher)) -> FileOperationResponse:
    """Trigger file discovery across all sources (GitHub, Local, SigmaRef)."""
    triggered = []
    busy = []

    if await _trigger_worker("github_discovery", {"task_type": "github_discovery", "collection_name": "all"}, dispatcher):
        triggered.append("github_discovery")
    else:
        busy.append("github_discovery")

    if await _trigger_worker("local_discovery", {"task_type": "local_discovery", "collection_name": "local"}, dispatcher):
        triggered.append("local_discovery")
    else:
        busy.append("local_discovery")

    if await _trigger_worker("sigmaref_discovery", {"task_type": "sigmaref_discovery", "collection_name": "sigmaref"}, dispatcher):
        triggered.append("sigmaref_discovery")
    else:
        busy.append("sigmaref_discovery")

    if busy:
        return FileOperationResponse(
            success=False,
            error=f"Workers already busy: {', '.join(busy)}",
            data={"triggered": triggered} if triggered else None,
        )

    return FileOperationResponse(
        success=True,
        message=f"Discovery queued for: {', '.join(triggered)}",
        data={"tasks": triggered},
    )


@router.post("/embed", response_model=FileOperationResponse)
async def file_embed(dispatcher: TaskDispatcher = Depends(_get_dispatcher)) -> FileOperationResponse:
    """Trigger file embedding across all sources (GitHub, Local, SigmaRef)."""
    triggered = []
    busy = []

    if await _trigger_worker("github_embeddings", {"task_type": "github_embeddings", "collection_name": "all"}, dispatcher):
        triggered.append("github_embeddings")
    else:
        busy.append("github_embeddings")

    if await _trigger_worker("local_embeddings", {"task_type": "local_embeddings", "collection_name": "local"}, dispatcher):
        triggered.append("local_embeddings")
    else:
        busy.append("local_embeddings")

    if await _trigger_worker("sigmaref_embeddings", {"task_type": "sigmaref_embeddings", "collection_name": "sigmaref"}, dispatcher):
        triggered.append("sigmaref_embeddings")
    else:
        busy.append("sigmaref_embeddings")

    if busy:
        return FileOperationResponse(
            success=False,
            error=f"Workers already busy: {', '.join(busy)}",
            data={"triggered": triggered} if triggered else None,
        )

    return FileOperationResponse(
        success=True,
        message=f"Embedding queued for: {', '.join(triggered)}",
        data={"tasks": triggered},
    )
