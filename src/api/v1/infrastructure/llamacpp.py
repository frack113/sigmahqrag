from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse

from src.api.sse import download_progress_generator
from src.application.system.health import HealthCheckService
from src.config.settings import get_config
from src.infrastructure.llm.llamacpp.service import get_llama_service
from src.shared.download_manager import create_download_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/llamacpp", tags=["v1-llamacpp"])

SERVICE_NAME = "llama.cpp"


_LLAMA_TERMINAL_STATUSES = frozenset({"completed", "updated", "cancelled", "failed"})


@router.get("/status")
async def llama_status():
    """Get status and version for llama service."""
    try:
        health_checker = HealthCheckService()
        version = health_checker.get_current_version(SERVICE_NAME)

        manager = create_download_manager()
        downloads = {
            k: {
                "status": v.status,
                "service": v.service,
                "version": v.version,
                "error": v.error,
                "bytes_downloaded": v.bytes_downloaded,
                "total_bytes": v.total_bytes,
                "speed_bps": v.speed_bps,
            }
            for k, v in manager.active_downloads.items()
            if v.service == SERVICE_NAME
        }

        config = get_config()
        return JSONResponse(
            content={
                "service": SERVICE_NAME,
                "mode": "managed" if config.llama_manage_internally else "external",
                "current_version": version or "unknown",
                "downloads": downloads,
            }
        )
    except Exception as e:
        logger.error(f"Llama status error: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


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
                    "message": result.get("message", "Version already up to date"),
                }
            )

        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Llama download error: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


@router.get("/progress/{download_id}")
async def llama_progress(download_id: str):
    """Stream progress for a specific llama download."""
    try:
        return StreamingResponse(
            download_progress_generator(download_id, terminal_statuses=_LLAMA_TERMINAL_STATUSES),
            media_type="text/event-stream",
        )
    except Exception as e:
        logger.error(f"Llama progress error: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


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

        service = get_llama_service()
        result = await service.start(model_path, port, context_size)
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Llama start error: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


@router.post("/stop")
async def llama_stop():
    """Stop the llama.cpp server."""
    try:
        service = get_llama_service()
        result = await service.stop()
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Llama stop error: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})
