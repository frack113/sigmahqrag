from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse

from src.back.backend.service_manager import create_service_manager
from src.back.backend.services.health_check import HealthCheckService
from src.back.download_manager import create_download_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/qdrant", tags=["v1-qdrant"])

SERVICE_NAME = "qdrant"


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


@router.get("/status")
async def qdrant_status():
    """Get status and version for qdrant service."""
    try:
        health_checker = HealthCheckService()
        version = health_checker.get_current_version(SERVICE_NAME)

        manager = create_download_manager()
        downloads = {
            k: {"status": v.status, "service": v.service, "version": v.version}
            for k, v in manager.active_downloads.items()
            if v.service == SERVICE_NAME
        }

        return JSONResponse(
            content={
                "service": SERVICE_NAME,
                "current_version": version or "unknown",
                "downloads": downloads,
            }
        )
    except Exception as e:
        logger.error(f"Qdrant status error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/progress/{download_id}")
async def qdrant_progress(download_id: str):
    """Stream progress for a specific qdrant download."""
    try:
        return StreamingResponse(
            _progress_generator(download_id),
            media_type="text/event-stream",
        )
    except Exception as e:
        logger.error(f"Qdrant progress error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/download")
async def qdrant_download(
    version: str = Query("latest", description="Version (default: latest)"),
):
    """Start a download for qdrant service."""
    try:
        manager = create_download_manager()
        result = await manager.start_download(SERVICE_NAME, version)

        if result.get("status") == "skipped":
            return JSONResponse(
                content={
                    "success": True,
                    "download_id": None,
                    "version": result.get("version"),
                    "message": result.get("message", "Version already installed"),
                }
            )

        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Qdrant download error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/stop")
async def qdrant_stop():
    """Stop the qdrant service."""
    try:
        service_manager = create_service_manager()
        result = await service_manager.stop_qdrant()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Qdrant stop error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/start")
async def qdrant_start(
    storage_path: str | None = Query(
        None, description="Path to storage directory (optional)"
    ),
):
    """Start the qdrant service."""
    try:
        if not storage_path:
            from src.shared import QDRANT_STORAGE_DIR
            storage_path = str(QDRANT_STORAGE_DIR)

        service_manager = create_service_manager()
        result = await service_manager.start_qdrant(storage_path=storage_path)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Qdrant start error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/restart")
async def qdrant_restart(
    storage_path: str | None = Query(
        None, description="Path to storage directory (optional)"
    ),
    port: int = Query(6333, description="Port to listen on"),
):
    """Restart the qdrant service."""
    try:
        if not storage_path:
            return JSONResponse(
                status_code=400,
                content={"error": "storage_path is required to restart the service"},
            )

        service_manager = create_service_manager()
        await service_manager.stop_qdrant()
        result = await service_manager.start_qdrant(
            storage_path=storage_path, port=port
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Qdrant restart error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

