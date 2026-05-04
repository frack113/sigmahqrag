"""API v1 backend routes for download and update operations."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse

from src.core.download_manager import (
    create_download_manager,
)
from src.core.update_manager import (
    create_update_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/backend", tags=["v1-backend"])

ALLOWED_SERVICES = {"llama", "qdrant"}
VALID_GET_ACTIONS = {"progress", "debug"}
VALID_POST_ACTIONS = {"download", "cancel"}


def _normalize_params(
    action: str, service: str | None = None
) -> tuple[str, str | None]:
    """Normalize action and service to lowercase for case-insensitive matching."""
    normalized_action = action.lower()
    normalized_service = service.lower() if service else None
    return normalized_action, normalized_service


async def _progress_generator(download_id: str) -> AsyncGenerator[str, None]:
    """Generate SSE progress updates."""
    manager = create_download_manager()
    queue = manager.get_progress_stream(download_id)

    if not queue:
        yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
        return

    while True:
        try:
            data = await asyncio.wait_for(queue.get(), timeout=30.0)
            yield f"data: {json.dumps(data)}\n\n"

            if data.get("status") in ("completed", "cancelled", "failed"):
                break
        except TimeoutError:
            yield f"data: {json.dumps({'status': 'timeout'})}\n\n"
            break


@router.get("/")
async def backend_get(
    action: str = Query(..., description="Action: progress, status"),
    service: str | None = Query(None, description="Service: llama, qdrant"),
    download_id: str | None = Query(None, description="Download ID for progress"),
):
    """Unified GET endpoint for backend operations (progress, status)."""
    try:
        action, service = _normalize_params(action, service)

        if action not in VALID_GET_ACTIONS:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid action"},
            )

        match action:
            case "progress":
                if not download_id:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "download_id required for progress"},
                    )
                return StreamingResponse(
                    _progress_generator(download_id),
                    media_type="text/event-stream",
                )

            case "debug":
                import psutil

                return JSONResponse(
                    content={
                        "cpu_percent": psutil.cpu_percent(),
                        "memory": psutil.virtual_memory()._asdict(),
                        "disk": psutil.disk_usage("/")._asdict(),
                    }
                )

    except Exception as e:
        logger.error(f"Backend GET error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@router.post("/")
async def backend_post(
    action: str = Query(..., description="Action: download, cancel"),
    service: str | None = Query(None, description="Service: llama, qdrant"),
    version: str | None = Query("latest", description="Version (default: latest)"),
    download_id: str | None = Query(None, description="Download ID to cancel"),
):
    """Unified POST endpoint for backend operations (download, cancel)."""
    try:
        action, service = _normalize_params(action, service)

        if action not in VALID_POST_ACTIONS:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid action"},
            )

        match action:
            case "download":
                if not service or service not in ALLOWED_SERVICES:
                    return JSONResponse(
                        status_code=400,
                        content={"error": f"Invalid service. Allowed: {ALLOWED_SERVICES}"},
                    )

                manager = create_download_manager()
                result = await manager.start_download(service, version)
                return JSONResponse(content=result)

            case "cancel":
                if not download_id:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "download_id required for cancel"},
                    )

                manager = create_download_manager()
                success = manager.cancel_download(download_id)
                return JSONResponse(
                    content={"success": success, "download_id": download_id}
                )

    except Exception as e:
        logger.error(f"Backend POST error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )