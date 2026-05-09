"""Centralized configuration API v1 — full sigmahqrag.toml management."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.shared import (
    load_config,
    set_backend_gpu_type,
    set_backend_os_type,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["config-v1"])


class ConfigUpdateRequest(BaseModel):
    """Request model for partial config update."""

    backend: dict[str, str] | None = None
    services: dict[str, Any] | None = None
    logging_cfg: dict[str, str] | None = None


@router.get("/config")
async def get_full_config() -> JSONResponse:
    """GET /v1/config — Return full application configuration from sigmahqrag.toml."""
    try:
        config = load_config()
        return JSONResponse(content={"status": "success", "data": config})
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return JSONResponse(
            status_code=500, content={"status": "error", "error": str(e)}
        )


@router.post("/config")
async def update_config(request: ConfigUpdateRequest) -> JSONResponse:
    """POST /v1/config — Update configuration and persist to sigmahqrag.toml."""
    try:
        if request.backend:
            os_val = request.backend.get("os")
            gpu_val = request.backend.get("gpu_type")

            if os_val:
                set_backend_os_type(os_val)
            if gpu_val:
                set_backend_gpu_type(gpu_val)

        return JSONResponse(
            content={
                "status": "success",
                "message": "Configuration updated and persisted",
                "data": load_config(),
            }
        )
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        return JSONResponse(
            status_code=500, content={"status": "error", "error": str(e)}
        )
