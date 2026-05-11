from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse

from src.back.backend.services.health_check import HealthCheckService
from src.back.llamacpp.service import create_llama_service
from src.shared.download_manager import create_download_manager

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

            if data.get("status") in ("completed", "updated", "cancelled", "failed"):
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


@router.post("/download")
async def llama_download(
    version: str = Query("latest", description="Version (default: latest)"),
):
    """Start a download for llama service."""
    try:
        manager = create_download_manager()
        result = await manager.start_download("llama.cpp", version)

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
        logger.error(f"Llama download error: {e}")
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


@router.post("/start")
async def llama_start(
    model_path: str | None = Query(None, description="Path to model file (optional)"),
    port: int = Query(8080, description="Port to listen on"),
    context_size: int = Query(4096, description="Context size in tokens"),
):
    """Start the llama.cpp server."""
    try:
        if not model_path:
            return JSONResponse(
                status_code=400,
                content={"error": "model_path is required to start the service"},
            )

        service = create_llama_service()
        result = await service.start(model_path, port, context_size)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Llama start error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/stop")
async def llama_stop():
    """Stop the llama.cpp server."""
    try:
        service = create_llama_service()
        result = await service.stop()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Llama stop error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/restart")
async def llama_restart(
    model_path: str | None = Query(None, description="Path to model file (optional)"),
    port: int = Query(8080, description="Port to listen on"),
    context_size: int = Query(4096, description="Context size in tokens"),
):
    """Restart the llama.cpp server."""
    try:
        if not model_path:
            return JSONResponse(
                status_code=400,
                content={"error": "model_path is required to restart the service"},
            )

        service = create_llama_service()
        await service.stop()
        result = await service.start(model_path, port, context_size)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Llama restart error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
