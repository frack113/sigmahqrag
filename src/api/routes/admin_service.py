"""Admin API routes for service management (unified action-based)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.admin.health import (
    ServiceHealth,
    ServiceStatus,
    create_health_checker,
)
from src.admin.service_manager import (
    create_service_manager,
)
from src.config import LLAMA_BIN_PATH, LOGS_DIR, MODELS_DIR, QDRANT_BIN_PATH

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
                _get_status_display(all_health["llama"], LLAMA_BIN_PATH),
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


def _normalize_params(action: str, service: str) -> tuple[str, str]:
    """Normalize action and service to lowercase for case-insensitive matching."""
    return action.lower(), service.lower()


@router.get(
    "/services/",
)
async def services_get(
    action: str = Query(..., description="Action: logs"),
    service: str = Query(..., description="Service: llama, qdrant"),
) -> JSONResponse:
    """Unified GET endpoint for service operations (logs)."""
    try:
        action, service = _normalize_params(action, service)

        if action not in VALID_GET_ACTIONS:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid action"},
            )

        if service not in ALLOWED_SERVICES:
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
    service: str = Query(..., description="Service: llama, qdrant"),
    request: StartRequest | None = None,
) -> JSONResponse:
    """Unified POST endpoint for service operations (start, stop)."""
    try:
        action, service = _normalize_params(action, service)

        if action not in VALID_POST_ACTIONS:
            return JSONResponse(
                status_code=400,
                content={"error": "Invalid action"},
            )

        if service not in ALLOWED_SERVICES:
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
                        if request and request.model_path:
                            candidate = Path(request.model_path)
                            # Validate: must be absolute path under MODELS_DIR
                            try:
                                resolved = candidate.resolve()
                                if not resolved.is_relative_to(MODELS_DIR):
                                    return JSONResponse(
                                        status_code=400,
                                        content={"success": False, "error": "Invalid model path"},
                                    )
                                if not resolved.is_file():
                                    return JSONResponse(
                                        status_code=400,
                                        content={"success": False, "error": "Model file not found"},
                                    )
                                model_path = str(resolved)
                            except (ValueError, RuntimeError):
                                return JSONResponse(
                                    status_code=400,
                                    content={"success": False, "error": "Invalid model path"},
                                )

                        # Pre-check: is service already running?
                        checker = create_health_checker()
                        health = await checker.check_all()
                        if service == "llama" and health["llama"].status.value == "running":
                            return JSONResponse(
                                status_code=400,
                                content={"success": False, "error": "llama.cpp is already running"},
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
                                content={"success": False, "error": "Qdrant is already running"},
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
                        if health["llama"].status.value != "running":
                            return JSONResponse(
                                status_code=400,
                                content={"success": False, "error": "llama.cpp is not running"},
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
                                content={"success": False, "error": "Qdrant is not running"},
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


class LlamaConfigRequest(BaseModel):
    """Request model for llama.cpp configuration."""
    os: str | None = None
    gpu: str | None = None


@router.get("/llama/config")
async def get_llama_config() -> JSONResponse:
    """Get llama.cpp configuration (OS, GPU)."""
    from src.config import get_backend_gpu_type, load_config

    try:
        config = load_config()
        gpu_type = get_backend_gpu_type()

        return JSONResponse(content={
            "gpu": gpu_type or "cpu",
            "os": "windows",
        })
    except Exception as e:
        logger.error(f"Failed to get llama config: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/llama/config")
async def set_llama_config(request: LlamaConfigRequest) -> JSONResponse:
    """Set llama.cpp configuration (OS, GPU)."""
    from src.config import set_backend_gpu_type

    try:
        if request.gpu:
            set_backend_gpu_type(request.gpu)

        return JSONResponse(content={
            "success": True,
            "message": f"GPU set to {request.gpu or 'cpu'}",
        })
    except Exception as e:
        logger.error(f"Failed to set llama config: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/llama/info")
async def get_llama_info() -> JSONResponse:
    """Get llama.cpp version and update info."""
    from src.admin.version_manager import (
        check_for_updates,
        get_current_version,
    )

    try:
        current = await get_current_version("llama.cpp")
        update_info = await check_for_updates("llama.cpp")

        return JSONResponse(content={
            "current_version": current,
            "update_available": update_info.get("update_available") if update_info else False,
            "latest_version": update_info.get("latest_version") if update_info else None,
        })
    except Exception as e:
        logger.error(f"Failed to get llama info: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/llama/download")
async def download_llama(
    request: LlamaConfigRequest | None = None,
) -> JSONResponse:
    """Download llama.cpp binary."""
    from src.admin.download_manager import create_download_manager

    try:
        dm = create_download_manager()
        result = await dm.start_download("llama.cpp", "latest")

        return JSONResponse(content={
            "success": True,
            "download_id": result.get("download_id"),
            "message": "Download started",
        })
    except Exception as e:
        logger.error(f"Failed to download llama.cpp: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/llama/update")
async def update_llama() -> JSONResponse:
    """Update llama.cpp to latest version."""
    from src.admin.download_manager import create_download_manager
    from src.admin.version_manager import VersionManager

    try:
        vm = VersionManager()
        release = await vm.get_release("llama.cpp", "latest")
        latest = release.tag_name.lstrip("v") if release.tag_name else "latest"

        dm = create_download_manager()
        result = await dm.start_download("llama.cpp", latest)

        return JSONResponse(content={
            "success": True,
            "download_id": result.get("download_id"),
            "version": latest,
            "message": f"Downloading llama.cpp v{latest}",
        })
    except Exception as e:
        logger.error(f"Failed to update llama.cpp: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
