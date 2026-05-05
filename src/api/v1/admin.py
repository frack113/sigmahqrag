"""Admin API v1 routes (Story 3.1 - GREEN phase)."""

from __future__ import annotations

import logging
import time
from typing import Any

from fastapi import APIRouter, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.config import load_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin-v1"])

# In-memory store for idempotency keys (ephemeral for MVP)
# Format: {key: (response_content, timestamp, endpoint)}
# TODO Growth: Replace with Redis for multi-worker support
_idempotency_store: dict[str, tuple[dict[str, Any], float, str]] = {}
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
        sorted_keys = sorted(
            _idempotency_store.keys(), key=lambda k: _idempotency_store[k][1]
        )
        for k in sorted_keys[: len(sorted_keys) // 2]:
            del _idempotency_store[k]


async def check_service_health() -> dict[str, Any]:
    """Check health of llama.cpp and Qdrant services (AC3 - <500ms by parallel checks)."""
    import asyncio

    from httpx import AsyncClient

    result: dict[str, Any] = {
        "llama_cpp": {"status": "unknown", "component": "llama.cpp", "port": 8080},
        "qdrant": {"status": "unknown", "component": "qdrant", "port": 6333},
    }

    async with AsyncClient() as client:
        # Parallel health checks to meet <500ms requirement (AC3)
        import asyncio

        llama_url = "http://localhost:8080/health"  # TODO Growth: from config
        qdrant_url = "http://localhost:6333/health"  # TODO Growth: from config

        async def check_llama():
            try:
                response = await client.get(llama_url, timeout=2.0)
                if (
                    response.status_code == 200
                    and response.json().get("status") == "healthy"
                ):
                    result["llama_cpp"]["status"] = "active"
                else:
                    result["llama_cpp"]["status"] = "inactive"
            except Exception:
                result["llama_cpp"]["status"] = "inactive"

        async def check_qdrant():
            try:
                response = await client.get(qdrant_url, timeout=2.0)
                if (
                    response.status_code == 200
                    and response.json().get("status") == "healthy"
                ):
                    result["qdrant"]["status"] = "active"
                else:
                    result["qdrant"]["status"] = "inactive"
            except Exception:
                result["qdrant"]["status"] = "inactive"

        await asyncio.gather(check_llama(), check_qdrant())

    return result


class DownloadRequest(BaseModel):
    """Request model for download action (Patch 13: Pydantic model)."""

    repo_url: str | None = None
    target_dir: str | None = None


class CancelRequest(BaseModel):
    """Request model for cancel action (Patch 13: Pydantic model)."""

    job_id: str


class JobResponse(BaseModel):
    """Response model for job actions (Patch 13: Pydantic model)."""

    job_id: str
    status: str


def start_download() -> dict[str, Any]:
    """Start download action and return job info (Patch 20: remove unnecessary async)."""
    import uuid

    return {"job_id": f"job-{uuid.uuid4().hex[:8]}", "status": "started"}


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
    """POST /api/v1/admin/download - Action-based endpoint (FR16, FR20, NFR20).

    Supports idempotency via X-Idempotency-Key header.
    Returns 503 if llama.cpp or Qdrant is down (FR17, NFR9, NFR10).
    """
    # Patch 11: Validate idempotency key
    if _is_valid_idempotency_key(x_idempotency_key):
        _cleanup_expired_entries()
        # Patch 10: Namespace per endpoint
        cache_key = f"download:{x_idempotency_key}"
        if cache_key in _idempotency_store:
            cached_content, _, _ = _idempotency_store[cache_key]
            return JSONResponse(content=cached_content)

    # Health check (fail-fast pattern)
    health = await check_service_health()

    if health["llama_cpp"]["status"] != "active":
        response = _build_error_response(
            status_code=503,
            error_type="service_unavailable",
            message="llama.cpp is not responding on port 8080",
            component="llama.cpp",
        )
        # Patch 4: Cache error responses too
        if _is_valid_idempotency_key(x_idempotency_key):
            _idempotency_store[f"download:{x_idempotency_key}"] = (
                response.content,
                time.time(),
                "download",
            )
        return response

    if health["qdrant"]["status"] != "active":
        response = _build_error_response(
            status_code=503,
            error_type="service_unavailable",
            message="Qdrant is not responding on port 6333",
            component="qdrant",
        )
        # Patch 4: Cache error responses too
        if _is_valid_idempotency_key(x_idempotency_key):
            _idempotency_store[f"download:{x_idempotency_key}"] = (
                response.content,
                time.time(),
                "download",
            )
        return response

    # Process download action
    result = await start_download()

    response_content = {"data": result, "status": "success"}

    # Patch 2,5: Store idempotency result with timestamp
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
                response.content,
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


@router.get("/models")
async def get_models() -> JSONResponse:
    """GET /api/v1/admin/models - Return installed models list."""
    from src.api.dependencies import get_model_manager

    try:
        mm = get_model_manager()
        models = await mm.list_installed_models()

        model_list = []
        for m in models:
            for filename, f in m.files.items():
                model_list.append(
                    {
                        "repo_id": m.repo_id,
                        "filename": filename,
                        "size_mb": f.file_size / (1024 * 1024) if f.file_size else 0,
                        "status": m.status.value,
                    }
                )

        return JSONResponse(
            content={"status": "success", "data": {"models": model_list}}
        )
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)},
        )


@router.post("/models/delete")
async def delete_model(request: dict) -> JSONResponse:
    """POST /api/v1/admin/models/delete - Delete a model."""
    from src.api.dependencies import get_model_manager
    from src.core.backend.services.manager import ModelNotFoundError

    try:
        repo_id = request.get("repo_id")
        filename = request.get("filename")

        if not repo_id or not filename:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": "repo_id and filename required"},
            )

        mm = get_model_manager()
        await mm.delete_model(repo_id, filename)

        return JSONResponse(
            content={"status": "success", "message": f"Deleted {repo_id}/{filename}"}
        )
    except ModelNotFoundError as e:
        return JSONResponse(
            status_code=404, content={"status": "error", "error": str(e)}
        )
    except Exception as e:
        logger.error(f"Failed to delete model: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)},
        )


@router.get("/config")
async def get_config() -> JSONResponse:
    """GET /api/v1/admin/config - Return app config."""
    try:
        config = load_config()
        return JSONResponse(content={"status": "success", "data": config})
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)},
        )
