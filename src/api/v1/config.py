"""Centralized configuration API v1 — full sigmahqrag.toml management."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.shared import get_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["config-v1"])


class ConfigUpdateRequest(BaseModel):
    """Request model for config updates."""

    backend: dict[str, Any] | None = None


@router.get("/config")
async def get_full_config() -> JSONResponse:
    """GET /v1/config — Return full application configuration from sigmahqrag.toml."""
    try:
        config = get_config()
        return JSONResponse(content={"status": "success", "data": config.to_dict()})
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})


@router.post("/config")
async def update_config(request: ConfigUpdateRequest) -> JSONResponse:
    """POST /v1/config — Update configuration and persist to sigmahqrag.toml."""
    try:
        config = get_config()
        if request.backend:
            os_val = request.backend.get("os")
            gpu_val = request.backend.get("gpu_type")

            if os_val:
                config.os = os_val
            if gpu_val:
                config.gpu_type = gpu_val

            config.save()

        return JSONResponse(
            content={
                "status": "success",
                "message": "Configuration updated and persisted",
                "data": config.to_dict(),
            }
        )
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        return JSONResponse(status_code=500, content={"status": "error", "error": str(e)})
