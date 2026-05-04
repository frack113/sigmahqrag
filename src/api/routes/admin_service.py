"""Admin API routes for service management (unified action-based)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.config import LLAMA_BIN_PATH, LOGS_DIR, QDRANT_BIN_PATH
from src.core.health import (
    ServiceHealth,
    ServiceStatus,
    create_health_checker,
)
from src.core.backend.service_manager import create_service_manager

logger = logging.getLogger(__name__)


def _get_status_display(health: ServiceHealth, binary_path: Path) -> dict[str, Any]:
    """Get display data for a service health status."""
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


class StartRequest(BaseModel):
    """Request model for starting a service."""

    model_path: str | None = None


router = APIRouter(prefix="/admin", tags=["admin-services"])

ALLOWED_SERVICES = {"llama", "qdrant"}
VALID_GET_ACTIONS = {"logs"}
VALID_POST_ACTIONS = {"start", "stop"}


@router.get(
    "/health",
)
async def get_admin_health() -> JSONResponse:
    """Get health status of all services for admin page."""
    try:
        checker = create_health_checker()
        all_health = await checker.check_all()

        result: dict[str, Any] = {
            "services": [
                _get_status_display(all_health["llamacpp"], LLAMA_BIN_PATH),
                _get_status_display(all_health["qdrant"], QDRANT_BIN_PATH),
            ],
        }

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


def _normalize_params(action: str, service: str | None) -> tuple[str, str | None]:
    """Normalize action and service to lowercase for case-insensitive matching."""
    return action.lower(), service.lower() if service else None


@router.get(
    "/services/",
)
async def services_get(
    action: str = Query(..., description="Action: logs"),
    service: str | None = Query(
        None, description="Service: llama, qdrant (optional for unified actions)"
    ),
) -> JSONResponse:
    """Unified GET endpoint for service operations (logs). Supports both individual and batch log retrieval."""
    try:
        action = _normalize_params(action, None)[0]

        if action not in VALID_GET_ACTIONS:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid action"},
            )

        # If no service specified, assume unified log retrieval for all services
        if not service:
            manager = create_service_manager()
            result = {"success": True, "logs": {}}

            try:
                logs_llama = manager.get_logs("llama.cpp")
                result["logs"]["llama.cpp"] = {
                    "service": "llama.cpp",
                    "log_file": str(LOGS_DIR / "llama.cpp.log"),
                    "logs": logs_llama,
                }
            except Exception as e:
                logger.error(f"Failed to read llama.cpp logs: {e}")
                result["logs"]["llama.cpp"] = {
                    "service": "llama.cpp",
                    "log_file": str(LOGS_DIR / "llama.cpp.log"),
                    "logs": "Error reading logs",
                    "error": str(e),
                }

            try:
                logs_qdrant = manager.get_logs("qdrant")
                result["logs"]["qdrant"] = {
                    "service": "qdrant",
                    "log_file": str(LOGS_DIR / "qdrant.log"),
                    "logs": logs_qdrant,
                }
            except Exception as e:
                logger.error(f"Failed to read qdrant logs: {e}")
                result["logs"]["qdrant"] = {
                    "service": "qdrant",
                    "log_file": str(LOGS_DIR / "qdrant.log"),
                    "logs": "Error reading logs",
                    "error": str(e),
                }

            return JSONResponse(content=result)

        # Proceed with individual service logic if a specific service is provided
        elif service not in ALLOWED_SERVICES:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid service"},
            )

        manager = create_service_manager()

        match action:
            case "logs":
                match service:
                    case "llama":
                        try:
                            logs = manager.get_logs("llama.cpp")
                        except Exception as e:
                            logger.error(f"Failed to read llama.cpp logs: {e}")
                            logs = "Error reading logs"
                        return JSONResponse(
                            content={
                                "service": "llama.cpp",
                                "log_file": str(LOGS_DIR / "llama.cpp.log"),
                                "logs": logs,
                            }
                        )
                    case "qdrant":
                        try:
                            logs = manager.get_logs("qdrant")
                        except Exception as e:
                            logger.error(f"Failed to read qdrant logs: {e}")
                            logs = "Error reading logs"
                        return JSONResponse(
                            content={
                                "service": "qdrant",
                                "log_file": str(LOGS_DIR / "qdrant.log"),
                                "logs": logs,
                            }
                        )

    except Exception as e:
        logger.error(f"Service GET action {action} failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )


@router.post(
    "/services/",
)
async def services_post(
    action: str = Query(..., description="Action: start, stop"),
    service: str | None = Query(
        None, description="Service: llama, qdrant (optional for unified actions)"
    ),
) -> JSONResponse:
    """Unified POST endpoint for service operations (start, stop). Supports both individual and batch service management."""
    try:
        action = _normalize_params(action, None)[0]

        if action not in VALID_POST_ACTIONS:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid action"},
            )

        # If no service specified, assume batch operation for all services
        if not service:
            manager = create_service_manager()

            match action:
                case "start":
                    results = {"success": True, "details": []}

                    # Start llama.cpp
                    checker = create_health_checker()
                    health = await checker.check_all()
                    if health["llamacpp"].status.value == "running":
                        results["details"].append(
                            {"service": "llama.cpp", "error": "Already running"}
                        )
                    else:
                        result_llama = await manager.start_llama(
                            model_path=str(LLAMA_BIN_PATH)
                        )
                        if not result_llama.get("success"):
                            results["details"].append(
                                {
                                    "service": "llama.cpp",
                                    "error": result_llama.get(
                                        "error", "Failed to start"
                                    ),
                                }
                            )

                    # Start Qdrant
                    if health["qdrant"].status.value == "running":
                        results["details"].append(
                            {"service": "Qdrant", "error": "Already running"}
                        )
                    else:
                        result_qdrant = await manager.start_qdrant()
                        if not result_qdrant.get("success"):
                            results["details"].append(
                                {
                                    "service": "Qdrant",
                                    "error": result_qdrant.get(
                                        "error", "Failed to start"
                                    ),
                                }
                            )

                    return JSONResponse(content=results)

                case "stop":
                    results = {"success": True, "details": []}

                    # Stop llama.cpp if running
                    checker = create_health_checker()
                    health = await checker.check_all()
                    if health["llamacpp"].status.value == "running":
                        result_llama = await manager.stop_llama()
                        if not result_llama.get("success"):
                            results["details"].append(
                                {
                                    "service": "llama.cpp",
                                    "error": result_llama.get(
                                        "error", "Failed to stop"
                                    ),
                                }
                            )
                    else:
                        results["details"].append(
                            {"service": "llama.cpp", "message": "Not running"}
                        )

                    # Stop Qdrant if running
                    if health["qdrant"].status.value == "running":
                        result_qdrant = await manager.stop_qdrant()
                        if not result_qdrant.get("success"):
                            results["details"].append(
                                {
                                    "service": "Qdrant",
                                    "error": result_qdrant.get(
                                        "error", "Failed to stop"
                                    ),
                                }
                            )
                    else:
                        results["details"].append(
                            {"service": "Qdrant", "message": "Not running"}
                        )

                    return JSONResponse(content=results)

        # Proceed with individual service logic if a specific service is provided
        elif service not in ALLOWED_SERVICES:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid service"},
            )

        manager = create_service_manager()

        match action:
            case "start":
                match service:
                    case "llama":
                        model_path = str(LLAMA_BIN_PATH)

                        # Pre-check: is service already running?
                        checker = create_health_checker()
                        health = await checker.check_all()
                        if health["llamacpp"].status.value == "running":
                            return JSONResponse(
                                status_code=400,
                                content={
                                    "success": False,
                                    "error": "llama.cpp is already running",
                                },
                            )

                        result = await manager.start_llama(model_path=model_path)

                        if result.get("success"):
                            pid = result.get("pid")
                            pid_str = str(pid) if pid is not None else "unknown"
                            return JSONResponse(
                                content={
                                    "success": True,
                                    "message": f"llama.cpp started (PID: {pid_str})",
                                    "pid": pid,
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
                    case "qdrant":
                        # Pre-check: is service already running?
                        checker = create_health_checker()
                        health = await checker.check_all()
                        if health["qdrant"].status.value == "running":
                            return JSONResponse(
                                status_code=400,
                                content={
                                    "success": False,
                                    "error": "Qdrant is already running",
                                },
                            )

                        result = await manager.start_qdrant()

                        if result.get("success"):
                            pid = result.get("pid")
                            pid_str = str(pid) if pid is not None else "unknown"
                            return JSONResponse(
                                content={
                                    "success": True,
                                    "message": f"Qdrant started (PID: {pid_str})",
                                    "pid": pid,
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
            case "stop":
                match service:
                    case "llama":
                        # Pre-check: is service running?
                        checker = create_health_checker()
                        health = await checker.check_all()
                        if health["llamacpp"].status.value != "running":
                            return JSONResponse(
                                status_code=400,
                                content={
                                    "success": False,
                                    "error": "llama.cpp is not running",
                                },
                            )

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
                    case "qdrant":
                        # Pre-check: is service running?
                        checker = create_health_checker()
                        health = await checker.check_all()
                        if health["qdrant"].status.value != "running":
                            return JSONResponse(
                                status_code=400,
                                content={
                                    "success": False,
                                    "error": "Qdrant is not running",
                                },
                            )

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
        logger.error(f"Service POST action {action} failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"},
        )



@router.post("/llama/download")
async def download_llama() -> JSONResponse:
    """Download llama.cpp binary."""
    from src.core.download_manager import create_download_manager

    try:
        dm = create_download_manager()
        result = await dm.start_download("llama.cpp", "latest")

        return JSONResponse(
            content={
                "success": True,
                "download_id": result.get("download_id"),
                "file_name": result.get("file_name"),
                "message": "Download started: "
                + (result.get("file_name") or "unknown"),
            }
        )
    except Exception as e:
        logger.error(f"Failed to download llama.cpp: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/qdrant/download")
async def download_qdrant() -> JSONResponse:
    """Download Qdrant binary."""
    from src.core.download_manager import create_download_manager

    try:
        dm = create_download_manager()
        result = await dm.start_download("qdrant", "latest")

        return JSONResponse(
            content={
                "success": True,
                "download_id": result.get("download_id"),
                "file_name": result.get("file_name"),
                "message": "Download started: "
                + (result.get("file_name") or "unknown"),
            }
        )
    except Exception as e:
        logger.error(f"Failed to download Qdrant: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/llama/update")
async def update_llama() -> JSONResponse:
    """Update llama.cpp to latest version."""
    from src.core.download_manager import create_download_manager
    from src.core.version_manager import VersionManager

    try:
        vm = VersionManager()
        release = await vm.get_release("llama.cpp", "latest")
        latest = release.tag_name.lstrip("v") if release.tag_name else "latest"

        dm = create_download_manager()
        result = await dm.start_download("llama.cpp", latest)

        return JSONResponse(
            content={
                "success": True,
                "download_id": result.get("download_id"),
                "version": latest,
                "message": f"Downloading llama.cpp v{latest}",
            }
        )
    except Exception as e:
        logger.error(f"Failed to update llama.cpp: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
