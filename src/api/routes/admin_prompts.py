"""Admin API routes for system prompt management."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.core.admin_prompts import (
    add_prompt,
    delete_prompt,
    get_active_prompt,
    get_prompt_content,
    list_prompts,
    set_active_prompt,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/prompts", tags=["admin-prompts"])


class AddPromptRequest(BaseModel):
    """Request model for adding a system prompt."""

    name: str
    content: str


class SetActiveRequest(BaseModel):
    """Request model for setting active prompt."""

    name: str


@router.get("/")
async def prompts_get(
    action: str = Query("list", description="Action: list, get, active"),
    name: str | None = Query(None, description="Prompt name"),
) -> JSONResponse:
    """Unified GET endpoint for system prompt operations."""
    try:
        match action:
            case "list":
                prompts = list_prompts()
                return JSONResponse(content=prompts)

            case "get":
                if not name:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "name required for action=get"},
                    )
                content = get_prompt_content(name)
                if content is None:
                    return JSONResponse(
                        status_code=404,
                        content={"error": f"Prompt '{name}' not found"},
                    )
                return JSONResponse(content={"name": name, "content": content})

            case "active":
                active = get_active_prompt()
                if active is None:
                    return JSONResponse(
                        status_code=404,
                        content={"error": "No active prompt set"},
                    )
                content = get_prompt_content(active)
                return JSONResponse(
                    content={
                        "active": active,
                        "content": content or "",
                    }
                )

            case _:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Unknown action: {action}"},
                )

    except Exception as e:
        logger.error(f"Prompt GET action {action} failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/")
async def prompts_post(
    action: str = Query("add", description="Action: add, delete, set_active"),
    request: AddPromptRequest | SetActiveRequest | None = None,
) -> JSONResponse:
    """Unified POST endpoint for system prompt write operations."""
    try:
        match action:
            case "add":
                if not request or not isinstance(request, AddPromptRequest):
                    return JSONResponse(
                        status_code=400,
                        content={"error": "name and content required"},
                    )
                result = add_prompt(request.name, request.content)
                status = 201 if result["success"] else 400
                return JSONResponse(status_code=status, content=result)

            case "delete":
                name = None
                if isinstance(request, SetActiveRequest):
                    name = request.name
                elif isinstance(request, AddPromptRequest):
                    name = request.name

                if not name:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "name required for action=delete"},
                    )
                result = delete_prompt(name)
                status = 200 if result["success"] else 404
                return JSONResponse(status_code=status, content=result)

            case "set_active":
                if not request or not isinstance(request, SetActiveRequest):
                    return JSONResponse(
                        status_code=400,
                        content={"error": "name required for action=set_active"},
                    )
                result = set_active_prompt(request.name)
                status = 200 if result["success"] else 400
                return JSONResponse(status_code=status, content=result)

            case _:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Unknown action: {action}"},
                )

    except Exception as e:
        logger.error(f"Prompt POST action {action} failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/active")
async def get_active() -> JSONResponse:
    """Get the active system prompt."""
    try:
        active = get_active_prompt()
        if active is None:
            return JSONResponse(
                status_code=404,
                content={"error": "No active prompt set"},
            )
        content = get_prompt_content(active)
        return JSONResponse(
            content={
                "active": active,
                "content": content or "",
            }
        )
    except Exception as e:
        logger.error(f"Failed to get active prompt: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
