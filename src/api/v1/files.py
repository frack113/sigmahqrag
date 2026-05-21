"""File Discovery and Embedding API v1."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from src.worker.processor import TaskDispatcher
from src.worker.enums import WorkerName

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


@router.post("/list", response_model=FileOperationResponse)
async def file_list(
    dispatcher: TaskDispatcher = Depends(_get_dispatcher),
) -> FileOperationResponse:
    """Trigger file discovery across all sources (GitHub, Local, SigmaRef)."""
    triggered = []
    busy = []

    if dispatcher.ask_for_worker(WorkerName.GITHUB_DISCOVERY, task_type=WorkerName.GITHUB_DISCOVERY.value, collection_name="all"):
        triggered.append(WorkerName.GITHUB_DISCOVERY.value)
    else:
        busy.append(WorkerName.GITHUB_DISCOVERY.value)

    if dispatcher.ask_for_worker(WorkerName.LOCAL_DISCOVERY, task_type=WorkerName.LOCAL_DISCOVERY.value, collection_name="local"):
        triggered.append(WorkerName.LOCAL_DISCOVERY.value)
    else:
        busy.append(WorkerName.LOCAL_DISCOVERY.value)

    if dispatcher.ask_for_worker(WorkerName.SIGMAREF_DISCOVERY, task_type=WorkerName.SIGMAREF_DISCOVERY.value, collection_name="sigmaref"):
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

    if dispatcher.ask_for_worker(WorkerName.GITHUB_EMBEDDINGS, task_type=WorkerName.GITHUB_EMBEDDINGS.value, collection_name="all"):
        triggered.append(WorkerName.GITHUB_EMBEDDINGS.value)
    else:
        busy.append(WorkerName.GITHUB_EMBEDDINGS.value)

    if dispatcher.ask_for_worker(WorkerName.LOCAL_EMBEDDINGS, task_type=WorkerName.LOCAL_EMBEDDINGS.value, collection_name="local"):
        triggered.append(WorkerName.LOCAL_EMBEDDINGS.value)
    else:
        busy.append(WorkerName.LOCAL_EMBEDDINGS.value)

    if dispatcher.ask_for_worker(WorkerName.SIGMAREF_EMBEDDINGS, task_type=WorkerName.SIGMAREF_EMBEDDINGS.value, collection_name="sigmaref"):
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
