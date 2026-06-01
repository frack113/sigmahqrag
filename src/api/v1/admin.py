"""Admin API v1 routes (Story 3.1 - GREEN phase)."""

from __future__ import annotations

import logging
import time
from typing import Any
from urllib.parse import urlparse

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.shared import get_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin-v1"])

# In-memory store for idempotency keys (ephemeral for MVP)
# Format: {key: (response_content, timestamp, endpoint)}
# TODO Growth: Replace with Redis for multi-worker support
_idempotency_store: dict[str, tuple[Any, float, str]] = {}
_IDEMPOTENCY_TTL = 3600  # 1 hour TTL for MVP
_IDEMPOTENCY_MAX_SIZE = 1000  # Prevent memory leaks


def _is_valid_idempotency_key(key: str | None) -> bool:
    """Validate idempotency key (Patch 11: reject empty strings)."""
    return key is not None and len(key.strip()) > 0


def _cleanup_expired_entries() -> None:
    """Remove expired entries (Patch 2: TTL support)."""
    now = time.time()
    expired_keys = [
        k for k, (_, ts, _) in _idempotency_store.items() if now - ts > _IDEMPOTENCY_TTL
    ]
    for k in expired_keys:
        del _idempotency_store[k]
    # Patch 2: Size limit
    if len(_idempotency_store) > _IDEMPOTENCY_MAX_SIZE:
        # Remove oldest entries
        sorted_keys = sorted(_idempotency_store.keys(), key=lambda k: _idempotency_store[k][1])
        for k in sorted_keys[: len(sorted_keys) // 2]:
            del _idempotency_store[k]


def _parse_llama_url(base_url: str) -> tuple[str, int]:
    """Extract host and port from a llama base URL.

    Returns:
        Tuple of (host, port). Defaults to (``127.0.0.1``, ``8080``).
    """
    parsed = urlparse(base_url.rstrip("/"))
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8080
    return host, port


async def check_service_health() -> dict[str, Any]:
    """Check health of llama.cpp and Qdrant services (AC3 - <500ms by parallel checks)."""
    import asyncio

    from httpx import AsyncClient

    from src.back.llamacpp import get_version as get_llama_version
    from src.back.qdrant import get_version as get_qdrant_version
    from src.shared import get_config

    config = get_config()
    llama_version = get_llama_version() or "Not installed"
    qdrant_version = get_qdrant_version() or "Not installed"

    base_url = config.llama_base_url or "http://127.0.0.1:8080"
    llama_host, llama_port = _parse_llama_url(base_url)
    qdrant_port = config.qdrant_port

    result: dict[str, Any] = {
        "llama_cpp": {
            "status": "unknown",
            "component": "llama.cpp",
            "port": llama_port,
            "version": llama_version,
        },
        "qdrant": {
            "status": "unknown",
            "component": "qdrant",
            "port": qdrant_port,
            "version": qdrant_version,
        },
    }

    async with AsyncClient() as client:

        async def check_llama():
            try:
                response = await client.get(f"http://{llama_host}:{llama_port}/health", timeout=2.0)
                # llama-server.exe returns {"status": "ok"} when ready, not
                # {"status": "healthy"} — the previous check was permanently
                # inactive even with a healthy server.
                if response.status_code == 200 and response.json().get("status") in {
                    "ok",
                    "healthy",
                }:
                    result["llama_cpp"]["status"] = "active"
            except Exception:
                result["llama_cpp"]["status"] = "inactive"

        async def check_qdrant():
            try:
                response = await client.get(f"http://localhost:{qdrant_port}/readyz", timeout=2.0)
                if response.status_code == 200:
                    result["qdrant"]["status"] = "active"
            except Exception:
                result["qdrant"]["status"] = "inactive"

        await asyncio.gather(check_llama(), check_qdrant())

    return result


@router.get("/backend")
async def get_backend() -> JSONResponse:
    """GET /api/v1/admin/backend - Return backend status and config."""
    try:
        health = await check_service_health()
        config = get_config()
        data = {
            "services": health,
            "config": config.to_dict(),
            "llama_mode": "managed" if config.llama_manage_internally else "external",
            "qdrant_mode": "managed" if config.qdrant_manage_internally else "external",
        }
        return JSONResponse(content={"data": data, "status": "success"})
    except Exception as e:
        logger.error(f"Backend status error: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


@router.post("/backend")
async def post_backend(request: dict) -> JSONResponse:
    """POST /api/v1/admin/backend - Start/stop services."""
    try:
        action = request.get("action")
        service = request.get("service")

        result: dict[str, Any]

        if action == "start" and service == "llama":
            from pathlib import Path

            from src.back.llamacpp.service import get_llama_service
            from src.shared import LLM_DIR

            models = list(Path(LLM_DIR).rglob("*.gguf"))
            model_path = str(models[0]) if models else None

            if not model_path:
                return JSONResponse(
                    content={
                        "data": {"success": False, "error": "No model found in models/llm"},
                        "status": "error",
                    }
                )

            base_url = get_config().llama_base_url or "http://127.0.0.1:8080"
            _, llama_port = _parse_llama_url(base_url)
            result = await get_llama_service().start(
                model_path=model_path, port=llama_port, context_size=4096
            )

        elif action == "stop" and service == "llama":
            from src.back.llamacpp.service import get_llama_service

            result = await get_llama_service().stop()

        elif action == "start" and service == "qdrant":
            from src.back.qdrant.service import get_qdrant_service

            result = await get_qdrant_service().start()

        elif action == "stop" and service == "qdrant":
            from src.back.qdrant.service import get_qdrant_service

            result = await get_qdrant_service().stop()

        else:
            result = {
                "success": False,
                "error": f"Unknown action/service: {action}/{service}",
            }

        return JSONResponse(
            content={
                "data": result,
                "status": "success" if result.get("success") else "error",
            }
        )
    except Exception as e:
        logger.error(f"Backend action error: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


class DownloadRequest(BaseModel):
    """Request model for download action."""

    action: str | None = "install"
    service: str | None = "qdrant"
    target: str | None = None


class CancelRequest(BaseModel):
    """Request model for cancel action (Patch 13: Pydantic model)."""

    job_id: str


async def start_download(service: str | None = None, target: str | None = None) -> dict[str, Any]:
    """Start download action and return job info."""
    import uuid

    from src.shared.download_manager import create_download_manager

    target_service = service or "qdrant"
    target_component = target or "all"

    job_id = f"job-{uuid.uuid4().hex[:8]}"

    if target_service == "llama":
        try:
            from src.back.llamacpp.auto_start import stop_llamacpp

            await stop_llamacpp()
        except Exception:
            pass

        try:
            manager = create_download_manager()
            result = await manager.start_download("llama.cpp", "latest")
            download_id = result.get("download_id")
            return {
                "job_id": job_id,
                "download_id": download_id,
                "status": result.get("status", "started"),
                "service": target_service,
                "message": result.get("message", "Download started"),
                "version": result.get("version"),
            }
        except Exception as e:
            logger.error(f"Llama download failed: {e}")
            return {
                "job_id": job_id,
                "status": "failed",
                "service": target_service,
                "error": str(e),
            }

    if target_service == "qdrant":
        from src.back.qdrant.downloader import (
            QDRANT_BINARY_VERSION,
            QDRANT_UI_VERSION,
            create_qdrant_installer,
        )

        installer = create_qdrant_installer()

        binary_result = {"success": False, "error": "skipped (binary running)"}
        ui_result = {"success": False, "error": "skipped"}

        if target_component in ("binary", "all"):
            binary_result = await installer.download_binary()
            if binary_result.get("success"):
                from src.shared import get_config

                config = get_config()
                config.qdrant_version = QDRANT_BINARY_VERSION
                config.save()

        if target_component in ("web_ui", "all"):
            ui_result = await installer.download_web_ui()
            if ui_result.get("success"):
                from src.shared import get_config

                config = get_config()
                config.qdrant_webui_version = QDRANT_UI_VERSION
                config.save()

        all_success = binary_result.get("success") and ui_result.get("success")
        any_success = binary_result.get("success") or ui_result.get("success")

        return {
            "job_id": job_id,
            "status": ("completed" if all_success else ("partial" if any_success else "failed")),
            "service": target_service,
            "binary_version": (QDRANT_BINARY_VERSION if binary_result.get("success") else None),
            "ui_version": QDRANT_UI_VERSION if ui_result.get("success") else None,
            "binary_error": (
                binary_result.get("error") if not binary_result.get("success") else None
            ),
            "ui_error": (ui_result.get("error") if not ui_result.get("success") else None),
        }

    return {
        "job_id": job_id,
        "status": "failed",
        "service": target_service,
        "error": f"Unsupported service: {target_service}",
    }


def _build_error_response(
    status_code: int, error_type: str, message: str, component: str
) -> JSONResponse:
    """Build structured JSON error response (NFR9, NFR10)."""
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "type": error_type,
                "message": message,
                "component": component,
                "code": status_code,
            }
        },
    )


@router.post("/download")
async def download_action(
    request: DownloadRequest | None = None,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> JSONResponse:
    """POST /api/v1/admin/download - Download/update services."""
    service = request.service if request else "qdrant"
    target = request.target if request else "all"

    if _is_valid_idempotency_key(x_idempotency_key):
        _cleanup_expired_entries()
        cache_key = f"download:{x_idempotency_key}"
        if cache_key in _idempotency_store:
            cached_content, _, _ = _idempotency_store[cache_key]
            return JSONResponse(content=cached_content)

    result = await start_download(service=service, target=target)

    response_content = {
        "data": result,
        "status": (
            "success"
            if result.get("status") in ("completed", "started")
            else result.get("status", "success")
        ),
    }

    if _is_valid_idempotency_key(x_idempotency_key):
        _idempotency_store[f"download:{x_idempotency_key}"] = (
            response_content,
            time.time(),
            "download",
        )

    return JSONResponse(content=response_content)


@router.get("/status")
async def get_status(
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> JSONResponse:
    """GET /api/v1/admin/status - Return component statuses (FR18).

    Note: Idempotency removed from GET (Patch 8: GET doesn't need idempotency).
    """
    health = await check_service_health()

    response_content = {"data": health, "status": "success"}

    return JSONResponse(content=response_content)


@router.post("/cancel")
async def cancel_action(
    request: CancelRequest,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> JSONResponse:
    """POST /api/v1/admin/cancel - Cancel a running job (FR16).

    Note: Only checks Qdrant health (Patch 9: no need for llama.cpp in cancel).
    """
    # Patch 11: Validate idempotency key
    if _is_valid_idempotency_key(x_idempotency_key):
        _cleanup_expired_entries()
        cache_key = f"cancel:{x_idempotency_key}"
        if cache_key in _idempotency_store:
            cached_content, _, _ = _idempotency_store[cache_key]
            return JSONResponse(content=cached_content)

    # Health check - only Qdrant needed for job tracking (Patch 9)
    health = await check_service_health()

    if health["qdrant"]["status"] != "active":
        response = _build_error_response(
            status_code=503,
            error_type="service_unavailable",
            message="Qdrant is not responding on port 6333",
            component="qdrant",
        )
        # Patch 4: Cache error responses too
        if _is_valid_idempotency_key(x_idempotency_key):
            _idempotency_store[f"cancel:{x_idempotency_key}"] = (
                response.body,
                time.time(),
                "cancel",
            )
        return response

    # Process cancel action
    # TODO: Add job tracking for Growth phase (Patch 14)
    job_id = request.job_id if request else "unknown"
    result = {"job_id": job_id, "status": "cancelled"}

    response_content = {"data": result, "status": "success"}

    # Patch 2,5: Store with timestamp and namespace
    if _is_valid_idempotency_key(x_idempotency_key):
        _idempotency_store[f"cancel:{x_idempotency_key}"] = (
            response_content,
            time.time(),
            "cancel",
        )

    return JSONResponse(content=response_content)


@router.get("/config")
async def admin_get_config() -> JSONResponse:
    """GET /api/v1/admin/config - Return app config."""
    try:
        config = get_config()
        return JSONResponse(content={"status": "success", "data": config.to_dict()})
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "An internal error occurred"},
        )
