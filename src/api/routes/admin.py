"""Admin API routes for service management."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, StreamingResponse

from src.admin.download_manager import (
    create_download_manager,
)
from src.admin.health import (
    ServiceHealth,
    ServiceStatus,
    create_health_checker,
)
from src.admin.update_manager import (
    create_update_service,
)
from src.api.dependencies import require_role
from src.auth.models import UserRole
from src.config import LLAMA_BIN_PATH, QDRANT_BIN_PATH
from src.schemas.download import (
    DownloadCancelRequest,
    DownloadRequest,
)
from src.schemas.update import (
    UpdateApplyRequest,
    UpdateRollbackRequest,
)

logger = logging.getLogger(__name__)


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


@router.get("/health", dependencies=[Depends(require_role(UserRole.ANALYST, UserRole.ADMIN))])
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




@router.post("/download", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def download_binary(request: DownloadRequest) -> JSONResponse:
    """Download a binary from GitHub releases.

    Args:
        request: DownloadRequest with service and version

    Returns:
        JSON with download_id, status, service, version, target_path
    """
    try:
        manager = create_download_manager()
        result = await manager.start_download(
            service=request.service,
            version=request.version,
        )

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Download failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@router.post("/download/cancel", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def cancel_download(request: DownloadCancelRequest) -> JSONResponse:
    """Cancel an active download.

    Args:
        request: DownloadCancelRequest with download_id

    Returns:
        JSON with download_id, status, message
    """
    try:
        manager = create_download_manager()
        result = await manager.cancel_download(request.download_id)

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Cancellation failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


async def _progress_generator(download_id: str) -> str:
    """Generate SSE progress updates.

    Args:
        download_id: Download ID

    Yields:
        SSE formatted progress data
    """
    manager = create_download_manager()
    queue = manager.get_progress_stream(download_id)

    if not queue:
        yield "data: {\"status\": \"not_found\"}\n\n"
        return

    while True:
        try:
            data = await asyncio.wait_for(queue.get(), timeout=30.0)
            yield f"data: {data}\n\n"

            if data.get("status") in ("completed", "cancelled", "failed"):
                break
        except TimeoutError:
            yield "data: {\"status\": \"timeout\"}\n\n"
            break


@router.get(
    "/download/{download_id}/progress",
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)
async def get_download_progress(download_id: str) -> StreamingResponse:
    """Get download progress via SSE.

    Args:
        download_id: Download ID

    Returns:
        StreamingResponse with SSE data
    """
    return StreamingResponse(
        _progress_generator(download_id),
        media_type="text/event-stream",
    )


@router.post("/update/apply", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def apply_update(request: UpdateApplyRequest) -> JSONResponse:
    """Apply an update to a service.

    Args:
        request: UpdateApplyRequest with service and version

    Returns:
        JSON with update result
    """
    try:
        update_service = create_update_service()

        from src.admin.version_manager import create_version_manager
        from src.config import BIN_DIR

        if request.service not in ("llama.cpp", "qdrant"):
            return JSONResponse(
                status_code=400,
                content={"error": f"Unsupported service: {request.service}"},
            )

        version_manager = create_version_manager()
        release = await version_manager.get_release(request.service, request.version)
        asset = version_manager.find_matching_asset(release, request.service)

        if not asset:
            return JSONResponse(
                status_code=400,
                content={"error": "No matching binary found for this platform"},
            )

        temp_dir = BIN_DIR / "pending"
        temp_dir.mkdir(parents=True, exist_ok=True)

        binary_path = temp_dir / f"{request.service.replace('.', '-')}"

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.get(
                asset.browser_download_url,
                follow_redirects=True,
            )
            response.raise_for_status()
            binary_path.write_bytes(response.content)

        result = await update_service.apply_update(
            service=request.service,
            version=request.version,
            binary_path=binary_path,
        )

        try:
            binary_path.unlink()
        except OSError:
            pass

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Update failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@router.post("/update/rollback", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def rollback_update(request: UpdateRollbackRequest) -> JSONResponse:
    """Rollback a service to previous version.

    Args:
        request: UpdateRollbackRequest with service

    Returns:
        JSON with rollback result
    """
    try:
        update_service = create_update_service()

        result = await update_service.rollback(service=request.service)

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )


@router.get("/update/status", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def get_update_status() -> JSONResponse:
    """Get update system status.

    Returns:
        JSON with current versions and available backups
    """
    try:
        update_service = create_update_service()

        result = await update_service.get_status()

        return JSONResponse(content=result)

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)},
        )
