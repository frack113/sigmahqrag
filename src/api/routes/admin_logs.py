"""API endpoint to view system logs."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-logs"])

LOG_PATH = Path("logs/sigmahqrag.log")


@router.get("/api/v1/admin/logs")
async def get_logs(
    lines: int = Query(default=100, ge=10, le=500),
    level: str = Query(default=""),
) -> JSONResponse:
    """Get recent log entries.

    Args:
        lines: Number of recent lines to return
        level: Filter by level (INFO, WARNING, ERROR)

    Returns:
        JSON with log entries
    """
    if not LOG_PATH.exists():
        return JSONResponse(
            content={"logs": [], "message": "Log file not found"}
        )

    try:
        with open(LOG_PATH, "r", encoding="utf-8") as f:
            all_lines = f.readlines()

        # Filter by level if specified
        if level:
            filtered = [l for l in all_lines if f" {level}:" in l]
        else:
            filtered = all_lines

        # Get last N lines
        recent = filtered[-lines:]

        entries = []
        for line in recent:
            entries.append({"text": line.strip()})

        return JSONResponse(content={"logs": entries, "total": len(entries)})

    except Exception as e:
        logger.error(f"Failed to read logs: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )
