"""Admin API v1 routes (Story 3.1 - GREEN phase)."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin-v1"])

# In-memory store for idempotency keys (ephemeral for MVP)
_idempotency_store: dict[str, Any] = {}


async def check_service_health() -> dict[str, Any]:
    """Check health of llama.cpp and Qdrant services."""
    import httpx

    result: dict[str, Any] = {
        "llama_cpp": {"status": "unknown", "component": "llama.cpp"},
        "qdrant": {"status": "unknown", "component": "qdrant"},
    }

    try:
        response = await httpx.AsyncClient().get("http://localhost:8080/health", timeout=2.0)
        if response.status_code == 200:
            result["llama_cpp"]["status"] = "active"
        else:
            result["llama_cpp"]["status"] = "inactive"
    except Exception:
        result["llama_cpp"]["status"] = "inactive"

    try:
        response = await httpx.AsyncClient().get("http://localhost:6333/health", timeout=2.0)
        if response.status_code == 200:
            result["qdrant"]["status"] = "active"
        else:
            result["qdrant"]["status"] = "inactive"
    except Exception:
        result["qdrant"]["status"] = "inactive"

    return result


async def start_download() -> dict[str, Any]:
    """Start download action and return job info."""
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
    request: Request,
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> JSONResponse:
    """POST /api/v1/admin/download - Action-based endpoint (FR16, FR20, NFR20).

    Supports idempotency via X-Idempotency-Key header.
    Returns 503 if llama.cpp or Qdrant is down (FR17, NFR9, NFR10).
    """
    # Check idempotency
    if x_idempotency_key and x_idempotency_key in _idempotency_store:
        return JSONResponse(content=_idempotency_store[x_idempotency_key])

    # Health check (fail-fast pattern)
    health = await check_service_health()

    if health["llama_cpp"]["status"] != "active":
        return _build_error_response(
            status_code=503,
            error_type="service_unavailable",
            message="llama.cpp is not responding on port 8080",
            component="llama.cpp",
        )

    if health["qdrant"]["status"] != "active":
        return _build_error_response(
            status_code=503,
            error_type="service_unavailable",
            message="Qdrant is not responding on port 6333",
            component="qdrant",
        )

    # Process download action
    result = await start_download()

    response_content = {"data": result, "status": "success"}

    # Store idempotency result
    if x_idempotency_key:
        _idempotency_store[x_idempotency_key] = response_content

    return JSONResponse(content=response_content)


@router.get("/status")
async def get_status(
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> JSONResponse:
    """GET /api/v1/admin/status - Return component statuses (FR18)."""
    # Check idempotency
    if x_idempotency_key and x_idempotency_key in _idempotency_store:
        return JSONResponse(content=_idempotency_store[x_idempotency_key])

    health = await check_service_health()

    response_content = {"data": health, "status": "success"}

    # Store idempotency result
    if x_idempotency_key:
        _idempotency_store[x_idempotency_key] = response_content

    return JSONResponse(content=response_content)


@router.post("/cancel")
async def cancel_action(
    request: dict[str, Any],
    x_idempotency_key: str | None = Header(default=None, alias="X-Idempotency-Key"),
) -> JSONResponse:
    """POST /api/v1/admin/cancel - Cancel a running job (FR16)."""
    # Check idempotency
    if x_idempotency_key and x_idempotency_key in _idempotency_store:
        return JSONResponse(content=_idempotency_store[x_idempotency_key])

    # Health check (fail-fast pattern)
    health = await check_service_health()

    if health["llama_cpp"]["status"] != "active":
        return _build_error_response(
            status_code=503,
            error_type="service_unavailable",
            message="llama.cpp is not responding on port 8080",
            component="llama.cpp",
        )

    if health["qdrant"]["status"] != "active":
        return _build_error_response(
            status_code=503,
            error_type="service_unavailable",
            message="Qdrant is not responding on port 6333",
            component="qdrant",
        )

    # Process cancel action
    job_id = request.get("job_id", "unknown")
    result = {"job_id": job_id, "status": "cancelled"}

    response_content = {"data": result, "status": "success"}

    # Store idempotency result
    if x_idempotency_key:
        _idempotency_store[x_idempotency_key] = response_content

    return JSONResponse(content=response_content)
