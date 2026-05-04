from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse

from src.core.download_manager import create_download_manager
from src.core.backend.services.health_check import HealthCheckService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/llamacpp", tags=["v1-llamacpp"])

SERVICE_NAME = "llama"

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
async def llama_status():
    """Get status and version for llama service."""
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
        logger.error(f"Llama status error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.get("/progress/{download_id}")
async def llama_progress(download_id: str):
    """Stream progress for a specific llama download."""
    try:
        return StreamingResponse(
            _progress_generator(download_id),
            media_type="text/event-stream",
        )
    except Exception as e:
        logger.error(f"Llama progress error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.post("/download")
async def llama_download(
    version: str = Query("latest", description="Version (default: latest)"),
):
    """Start a download for llama service."""
    try:
        manager = create_download_manager()
        result = await manager.start_download(SERVICE_NAME, version)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Llama download error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.post("/cancel/{download_id}")
async def llama_cancel(download_id: str):
    """Cancel a llama download."""
    try:
        manager = create_download_manager()
        success = manager.cancel_download(download_id)
        return JSONResponse(content={"success": success, "download_id": download_id})
    except Exception as e:
        logger.error(f"Llama cancel error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
