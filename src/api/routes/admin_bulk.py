"""Bulk actions API for admin operations."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-bulk"])


@router.post("/api/v1/admin/bulk-delete-models")
async def bulk_delete_models(request: list[dict[str, str]]) -> JSONResponse:
    """Bulk delete multiple models.

    Args:
        request: List of {repo_id, filename} objects

    Returns:
        JSON with deleted count and errors
    """
    if not request or len(request) > 10:
        raise HTTPException(
            status_code=400,
            detail="Invalid request: max 10 items",
        )

    from src.core.services import ModelManager

    mm = ModelManager()
    deleted = []
    errors = []

    for item in request:
        repo_id = item.get("repo_id")
        filename = item.get("filename")
        if not repo_id or not filename:
            errors.append(f"Invalid item: {item}")
            continue

        try:
            await mm.delete_model(repo_id, filename)
            deleted.append(f"{repo_id}/{filename}")
        except Exception as e:
            errors.append(f"Failed to delete {repo_id}/{filename}: {e}")

    return JSONResponse(
        content={
            "deleted": deleted,
            "errors": errors,
            "count": len(deleted),
        }
    )
