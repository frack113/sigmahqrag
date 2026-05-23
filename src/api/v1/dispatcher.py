"""TaskDispatcher API v1 routes."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from src.api.dependencies import get_dispatcher
from src.worker.enums import WorkerName, WorkerStatus
from src.worker.processor import TaskDispatcher

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/dispatcher", tags=["v1-dispatcher"])


class AskWorkerRequest(BaseModel):
    worker_type: str
    task_params: dict = {}


@router.get("/progress/{worker_type}")
async def worker_progress(worker_type: str, dispatcher: TaskDispatcher = Depends(get_dispatcher)):
    """Get progress percentage (0–100) for a worker type."""
    try:
        worker_enum = WorkerName(worker_type)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unknown worker type: {worker_type}"},
        )
    progress = dispatcher.get_progress_worker(worker_enum)
    return JSONResponse(content={"worker_type": worker_type, "progress_percent": progress})


@router.post("/ask")
async def ask_worker(
    request: AskWorkerRequest,
    dispatcher: TaskDispatcher = Depends(get_dispatcher),
):
    """Request a worker to start a task. Returns task_id on success."""
    try:
        worker_enum = WorkerName(request.worker_type)
    except ValueError:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unknown worker type: {request.worker_type}"},
        )
    task_id = dispatcher.ask_for_worker(worker_enum, **request.task_params)
    if task_id is None:
        return JSONResponse(
            status_code=409,
            content={"error": "worker_busy", "message": "Worker is busy"},
        )
    return JSONResponse(content={"task_id": task_id, "worker_type": request.worker_type})


@router.get("/status/{worker_type}")
async def worker_status(worker_type: str, dispatcher: TaskDispatcher = Depends(get_dispatcher)):
    """Get full status details for a worker type."""
    status_data = dispatcher.get_worker_progress(worker_type)
    if not status_data:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "message": "Worker not found"},
        )
    return JSONResponse(content={"worker_type": worker_type, **status_data})


@router.get("/status/{worker_type}/stream")
async def worker_status_stream(
    worker_type: str, dispatcher: TaskDispatcher = Depends(get_dispatcher)
):
    """Stream SSE progress updates for a worker type."""

    async def _progress_generator() -> AsyncGenerator[str, None]:
        while True:
            try:
                status_data = dispatcher.get_worker_progress(worker_type)
                if not status_data:
                    yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
                    break

                yield f"data: {json.dumps(status_data)}\n\n"

                if status_data.get("status") in (WorkerStatus.IDLE.value, WorkerStatus.ERROR.value):
                    break
            except Exception as e:
                logger.error(f"SSE error for {worker_type}: {e}")
                yield f"data: {json.dumps({'status': 'error', 'message': 'An internal error occurred'})}\n\n"
                break

            await asyncio.sleep(2)

    try:
        return StreamingResponse(
            _progress_generator(),
            media_type="text/event-stream",
        )
    except Exception as e:
        logger.error(f"stream error for {worker_type}: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


@router.get("/status")
async def all_worker_status(dispatcher: TaskDispatcher = Depends(get_dispatcher)):
    """Get status of all workers."""
    states = dispatcher.get_all_worker_states()
    return JSONResponse(content={"workers": states})
