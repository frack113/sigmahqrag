"""Admin API routes for service management."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from sigmahqrag.admin.health import (
    ServiceHealth,
    ServiceStatus,
    create_health_checker,
)
from sigmahqrag.admin.service_manager import (
    create_service_manager,
)
from sigmahqrag.config import LLAMA_BIN_PATH, LOGS_DIR, QDRANT_BIN_PATH

logger = logging.getLogger(__name__)


class StartRequest(BaseModel):
    """Request model for starting a service."""

    model_path: str | None = None


class StopRequest(BaseModel):
    """Request model for stopping a service."""

    pass


router = APIRouter(prefix="/admin", tags=["admin"])


def _get_status_display(health: ServiceHealth, binary_path: Path) -> dict[str, Any]:
    """Get display data for a service health status.

    Args:
        health: ServiceHealth object
        binary_path: Path to the service binary

    Returns:
        Dict with display data
    """
    if health.status == ServiceStatus.RUNNING:
        color = "green"
        display_status = "running"
    elif health.status == ServiceStatus.STOPPED:
        color = "red"
        display_status = "stopped"
    else:
        color = "yellow"
        display_status = "unknown"

    result: dict[str, Any] = {
        "name": health.name,
        "status": display_status,
        "color": color,
        "port": health.port,
        "url": health.url,
    }

    if health.message:
        result["message"] = health.message

    if not binary_path.exists():
        result["status"] = "not installed"
        result["color"] = "yellow"
        result["message"] = "Binary not found"

    return result


@router.get("/health")
async def get_admin_health() -> JSONResponse:
    """Get health status of all services for admin page.

    Returns:
        JSON with service statuses and display info
    """
    try:
        checker = create_health_checker()
        all_health = await checker.check_all()

        result: dict[str, Any] = {
            "services": [
                _get_status_display(all_health["llama"], LLAMA_BIN_PATH),
                _get_status_display(all_health["qdrant"], QDRANT_BIN_PATH),
            ],
        }

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@router.post("/llama/start")
async def start_llama(request: StartRequest | None = None) -> JSONResponse:
    """Start llama.cpp server.

    Args:
        request: Optional StartRequest with model_path

    Returns:
        JSON with start result
    """
    try:
        manager = create_service_manager()

        model_path = str(LLAMA_BIN_PATH)
        if request and request.model_path:
            model_path = request.model_path

        result = await manager.start_llama(model_path=model_path)

        if result.get("success"):
            return JSONResponse(
                content={
                    "success": True,
                    "message": f"llama.cpp started (PID: {result.get('pid')})",
                    "pid": result.get("pid"),
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": result.get("error", "Failed to start"),
                },
            )

    except Exception as e:
        logger.error(f"Failed to start llama.cpp: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@router.post("/llama/stop")
async def stop_llama() -> JSONResponse:
    """Stop llama.cpp server.

    Returns:
        JSON with stop result
    """
    try:
        manager = create_service_manager()
        result = await manager.stop_llama()

        if result.get("success"):
            return JSONResponse(
                content={
                    "success": True,
                    "message": "llama.cpp stopped",
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": result.get("error", "Failed to stop"),
                },
            )

    except Exception as e:
        logger.error(f"Failed to stop llama.cpp: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@router.post("/qdrant/start")
async def start_qdrant() -> JSONResponse:
    """Start Qdrant server.

    Returns:
        JSON with start result
    """
    try:
        manager = create_service_manager()
        result = await manager.start_qdrant()

        if result.get("success"):
            return JSONResponse(
                content={
                    "success": True,
                    "message": f"Qdrant started (PID: {result.get('pid')})",
                    "pid": result.get("pid"),
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": result.get("error", "Failed to start"),
                },
            )

    except Exception as e:
        logger.error(f"Failed to start Qdrant: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@router.post("/qdrant/stop")
async def stop_qdrant() -> JSONResponse:
    """Stop Qdrant server.

    Returns:
        JSON with stop result
    """
    try:
        manager = create_service_manager()
        result = await manager.stop_qdrant()

        if result.get("success"):
            return JSONResponse(
                content={
                    "success": True,
                    "message": "Qdrant stopped",
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": result.get("error", "Failed to stop"),
                },
            )

    except Exception as e:
        logger.error(f"Failed to stop qdrant: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@router.get("/llama/logs")
async def get_llama_logs() -> JSONResponse:
    """Get llama.cpp logs.

    Returns:
        JSON with log content
    """
    try:
        manager = create_service_manager()
        logs = manager.get_logs("llama.cpp")

        return JSONResponse(
            content={
                "service": "llama.cpp",
                "log_file": str(LOGS_DIR / "llama.cpp.log"),
                "logs": logs,
            }
        )

    except Exception as e:
        logger.error(f"Failed to get llama.cpp logs: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@router.get("/qdrant/logs")
async def get_qdrant_logs() -> JSONResponse:
    """Get Qdrant logs.

    Returns:
        JSON with log content
    """
    try:
        manager = create_service_manager()
        logs = manager.get_logs("qdrant")

        return JSONResponse(
            content={
                "service": "qdrant",
                "log_file": str(LOGS_DIR / "qdrant.log"),
                "logs": logs,
            }
        )

    except Exception as e:
        logger.error(f"Failed to get qdrant logs: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )
