"""Admin backend API routes for download and update operations (unified action-based)."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse

from src.admin.download_manager import (
    create_download_manager,
)
from src.admin.update_manager import (
    create_update_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin-backend"])

ALLOWED_SERVICES = {"llama", "qdrant"}
VALID_GET_ACTIONS = {"progress", "status", "debug"}
VALID_POST_ACTIONS = {"download", "cancel"}


def _normalize_params(action: str, service: str | None = None) -> tuple[str, str | None]:
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


@router.get(
    "/backend/",
)
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
                        content={"error": "download_id required for action=progress"},
                    )
                return StreamingResponse(
                    _progress_generator(download_id),
                    media_type="text/event-stream",
                )

            case "status":
                update_service = create_update_service()
                result = await update_service.get_status()

                # Add active downloads (optionally filtered by service)
                dm = create_download_manager()
                downloads = {}
                service_normalized = service.replace(".","") if service else None
                for dl_id, task in dm.active_downloads.items():
                    task_service_normalized = task.service.replace(".","") if task.service else None
                    if service and task_service_normalized != service_normalized:
                        continue
                    downloads[dl_id] = {
                        "service": task.service,
                        "status": task.status,
                        "bytes_downloaded": task.bytes_downloaded,
                        "total_bytes": task.total_bytes,
                    }
                result["downloads"] = downloads
                return JSONResponse(content=result)

            case "debug":
                dm = create_download_manager()
                return JSONResponse(content={
                    "active_downloads": {
                        dl_id: {
                            "service": task.service,
                            "status": task.status,
                            "bytes_downloaded": task.bytes_downloaded,
                            "total_bytes": task.total_bytes,
                        }
                        for dl_id, task in dm.active_downloads.items()
                    }
                })

            case _:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid action"},
                )

    except Exception as e:
        logger.error(f"Backend GET action {action} failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.post(
    "/backend/",
)
async def backend_post(
    action: str = Query(..., description="Action: download, cancel"),
    service: str | None = Query(None, description="Service: llama, qdrant (optional for unified actions)"),
    version: str | None = Query(None, description="Version for download (default: latest)"),
    download_id: str | None = Query(None, description="Download ID for cancel"),
) -> JSONResponse:
    """Unified POST endpoint for backend operations (download, cancel). Supports both individual and batch service management."""
    try:
        action, _ = _normalize_params(action, None)

        if action not in VALID_POST_ACTIONS:
            return JSONResponse(
                status_code=400,
                content={"error": f"Invalid action: {action}. Allowed actions are: {VALID_POST_ACTIONS}"},
            )

        match action:
            case "download":
                if not service or service not in ALLOWED_SERVICES:
                    return JSONResponse(
                        status_code=400,
                        content={"error": f"Valid service required (llama, qdrant). Got: {service}"},
                    )

                # Map service names to their actual values (e.g., 'llama' -> 'llama.cpp')
                service_name = "llama.cpp" if service == "llama" else "qdrant"
                manager = create_download_manager()
                result = await manager.start_download(
                    service=service_name,
                    version=version or "latest",
                )
                return JSONResponse(content=result)

            case "cancel":
                if not download_id:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "download_id required for action=cancel"},
                    )

                manager = create_download_manager()
                result = await manager.cancel_download(download_id)
                return JSONResponse(content=result)

            case "cancel":
                if not download_id:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "download_id required for action=cancel"},
                    )

                manager = create_download_manager()
                result = await manager.cancel_download(download_id)
                return JSONResponse(content=result)

            case _:
                return JSONResponse(
                    status_code=400,
                    content={"error": "Invalid action"},
                )

    except Exception as e:
        logger.error(f"Backend POST action {action} failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Internal server error: {str(e)}"},
        )
