"""Centralized configuration API v1 — backend config (DuckDB) + remaining TOML settings."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

from src.config.settings import get_config
from src.infrastructure.database.service import DatabaseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["config-v1"])

LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})


class ConfigUpdateRequest(BaseModel):
    """Request model for config updates."""

    backend: dict[str, Any] | None = None


class LoggingConfigUpdateRequest(BaseModel):
    """Request model for logging config updates."""

    level: str | None = None
    log_max_size: str | None = None
    log_max_file: int | None = None
    clean_at_startup: bool | None = None

    @field_validator("level")
    @classmethod
    def validate_level(cls, v):
        if v is not None and v not in LOG_LEVELS:
            raise ValueError(f"Invalid log level: {v}")
        return v


@router.get("/config")
async def get_full_config() -> JSONResponse:
    """GET /api/v1/config — Return full application configuration."""
    try:
        config = get_config()
        return JSONResponse(content={"status": "success", "data": config.to_dict()})
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        return JSONResponse(
            status_code=500, content={"status": "error", "error": "An internal error occurred"}
        )


@router.get("/config/logging")
async def get_logging_config() -> JSONResponse:
    """GET /api/v1/config/logging — Return logging configuration."""
    try:
        config = get_config()
        return JSONResponse(
            content={
                "status": "success",
                "data": {
                    "level": config.logging_level,
                    "log_max_size": config.logging_log_max_size,
                    "log_max_file": config.logging_log_max_file,
                    "clean_at_startup": config.logging_clean_at_startup,
                },
            }
        )
    except Exception as e:
        logger.error(f"Failed to load logging config: {e}")
        return JSONResponse(
            status_code=500, content={"status": "error", "error": "An internal error occurred"}
        )


@router.post("/config/logging")
async def update_logging_config(request: LoggingConfigUpdateRequest) -> JSONResponse:
    """POST /api/v1/config/logging — Update logging config persisted to DuckDB."""
    try:
        config = get_config()
        db = DatabaseService.get_instance()

        if request.level is not None:
            config.logging_level = request.level
            db.set_config("logging.level", request.level)
        if request.log_max_size is not None:
            config.logging_log_max_size = request.log_max_size
            db.set_config("logging.log_max_size", request.log_max_size)
        if request.log_max_file is not None:
            config.logging_log_max_file = request.log_max_file
            db.set_config("logging.log_max_file", request.log_max_file)
        if request.clean_at_startup is not None:
            config.logging_clean_at_startup = request.clean_at_startup
            db.set_config("logging.clean_at_startup", request.clean_at_startup)

        return JSONResponse(
            content={
                "status": "success",
                "message": "Logging configuration updated",
                "data": {
                    "level": config.logging_level,
                    "log_max_size": config.logging_log_max_size,
                    "log_max_file": config.logging_log_max_file,
                    "clean_at_startup": config.logging_clean_at_startup,
                },
            }
        )
    except Exception as e:
        logger.error(f"Failed to update logging config: {e}")
        return JSONResponse(
            status_code=500, content={"status": "error", "error": "An internal error occurred"}
        )


@router.post("/config")
async def update_config(request: ConfigUpdateRequest) -> JSONResponse:
    """POST /api/v1/config — Update backend config (os, gpu_type) persisted to DuckDB."""
    try:
        config = get_config()
        if request.backend:
            os_val = request.backend.get("os")
            gpu_val = request.backend.get("gpu_type")

            if os_val:
                config.os = os_val
            if gpu_val:
                config.gpu_type = gpu_val

            db = DatabaseService.get_instance()
            if os_val is not None:
                db.set_config("backend.os", os_val)
            if gpu_val is not None:
                db.set_config("backend.gpu_type", gpu_val)

        return JSONResponse(
            content={
                "status": "success",
                "message": "Configuration updated and persisted",
                "data": config.to_dict(),
            }
        )
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        return JSONResponse(
            status_code=500, content={"status": "error", "error": "An internal error occurred"}
        )
