"""File Discovery and Embedding API v1."""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from src.worker.processor import TaskDispatcher
from src.worker.enums import WorkerName, WorkerStatus

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


def _trigger_worker(worker_type: WorkerName, task: dict, dispatcher: TaskDispatcher) -> bool:
    """Helper to trigger a worker via the dispatcher."""
    if dispatcher.is_worker_busy(worker_type):
        return False

    task_id = str(uuid.uuid4())
    task["task_id"] = task_id
    dispatcher.update_worker_state(
        worker_type=worker_type,
        status=WorkerStatus.RUNNING,
        current_task_id=task_id,
    )

    dispatcher.queue_task(worker_type, task)
    return True


@router.post("/list", response_model=FileOperationResponse)
async def file_list(
    dispatcher: TaskDispatcher = Depends(_get_dispatcher),
) -> FileOperationResponse:
    """Trigger file discovery across all sources (GitHub, Local, SigmaRef)."""
    triggered = []
    busy = []

    if _trigger_worker(WorkerName.GITHUB_DISCOVERY, {"task_type": WorkerName.GITHUB_DISCOVERY.value, "collection_name": "all"}, dispatcher):
        triggered.append(WorkerName.GITHUB_DISCOVERY.value)
    else:
        busy.append(WorkerName.GITHUB_DISCOVERY.value)

    if _trigger_worker(WorkerName.LOCAL_DISCOVERY, {"task_type": WorkerName.LOCAL_DISCOVERY.value, "collection_name": "local"}, dispatcher):
        triggered.append(WorkerName.LOCAL_DISCOVERY.value)
    else:
        busy.append(WorkerName.LOCAL_DISCOVERY.value)

    if _trigger_worker(WorkerName.SIGMAREF_DISCOVERY, {"task_type": WorkerName.SIGMAREF_DISCOVERY.value, "collection_name": "sigmaref"}, dispatcher):
        triggered.append(WorkerName.SIGMAREF_DISCOVERY.value)
    else:
        busy.append(WorkerName.SIGMAREF_DISCOVERY.value)

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
async def file_embed(
    dispatcher: TaskDispatcher = Depends(_get_dispatcher),
) -> FileOperationResponse:
    """Trigger file embedding across all sources (GitHub, Local, SigmaRef)."""
    triggered = []
    busy = []

    if _trigger_worker(WorkerName.GITHUB_EMBEDDINGS, {"task_type": WorkerName.GITHUB_EMBEDDINGS.value, "collection_name": "all"}, dispatcher):
        triggered.append(WorkerName.GITHUB_EMBEDDINGS.value)
    else:
        busy.append(WorkerName.GITHUB_EMBEDDINGS.value)

    if _trigger_worker(WorkerName.LOCAL_EMBEDDINGS, {"task_type": WorkerName.LOCAL_EMBEDDINGS.value, "collection_name": "local"}, dispatcher):
        triggered.append(WorkerName.LOCAL_EMBEDDINGS.value)
    else:
        busy.append(WorkerName.LOCAL_EMBEDDINGS.value)

    if _trigger_worker(WorkerName.SIGMAREF_EMBEDDINGS, {"task_type": WorkerName.SIGMAREF_EMBEDDINGS.value, "collection_name": "sigmaref"}, dispatcher):
        triggered.append(WorkerName.SIGMAREF_EMBEDDINGS.value)
    else:
        busy.append(WorkerName.SIGMAREF_EMBEDDINGS.value)

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
