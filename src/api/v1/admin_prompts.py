"""Prompts API for system prompt management."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.core.admin_prompts import (
    add_prompt,
    delete_prompt,
    get_prompt_content,
    list_prompts,
    set_active_prompt,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/prompts", tags=["v1-prompts"])


class AddPromptRequest(BaseModel):
    """Request model for adding a system prompt."""

    name: str
    content: str


class SetActiveRequest(BaseModel):
    """Request model for setting active prompt."""

    name: str


@router.get("")
async def prompts_get(
    action: str = Query("list", alias="action"),
    name: str = Query(None),
) -> JSONResponse:
    """GET prompts - list, get content, or get active."""
    try:
        if action == "list" or action is None:
            prompts = list_prompts()
            return JSONResponse(content=prompts)
        elif action == "active":
            from src.core.admin_prompts import get_active_prompt

            active = get_active_prompt()
            return JSONResponse(content={"name": active})
        elif action == "get" and name:
            content = get_prompt_content(name)
            if content is None:
                return JSONResponse(
                    status_code=404, content={"error": f"Prompt '{name}' not found"}
                )
            return JSONResponse(content={"name": name, "content": content})
        else:
            return JSONResponse(status_code=400, content={"error": "Invalid action"})
    except Exception as e:
        logger.error(f"Prompts GET failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("")
async def prompts_post(
    action: str = Query(None),
    name: str = Query(None),
    content: str = Query(None),
) -> JSONResponse:
    """POST prompts - add/activate/delete."""
    try:
        if action == "activate" and name:
            set_active_prompt(name)
            return JSONResponse(content={"message": f"Prompt '{name}' activated"})
        elif name and content:
            add_prompt(name, content)
            return JSONResponse(content={"message": f"Prompt '{name}' saved"})
        elif action == "delete" and name:
            delete_prompt(name)
            return JSONResponse(content={"message": f"Prompt '{name}' deleted"})
        else:
            return JSONResponse(status_code=400, content={"error": "Invalid request"})
    except Exception as e:
        logger.error(f"Prompts POST failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.delete("")
async def prompts_delete(
    name: str = Query(..., description="Prompt name"),
) -> JSONResponse:
    """Delete a prompt."""
    try:
        delete_prompt(name)
        return JSONResponse(content={"message": f"Prompt '{name}' deleted"})
    except Exception as e:
        logger.error(f"Failed to delete prompt: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
