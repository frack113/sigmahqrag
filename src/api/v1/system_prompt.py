"""Prompts API for system prompt management."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from src.back.system_prompt import (
    add_prompt,
    delete_prompt,
    get_active_prompt,
    get_prompt_by_id,
    get_prompt_by_name,
    list_prompts,
    set_active_prompt,
    update_prompt,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin/prompts", tags=["v1-prompts"])

NAME_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"


class AddPromptRequest(BaseModel):
    """Request model for adding a system prompt."""

    name: str = Field(..., max_length=25, pattern=NAME_PATTERN)
    content: str
    description: str = Field("", max_length=100)


class UpdatePromptRequest(BaseModel):
    """Request model for updating a system prompt."""

    name: str | None = Field(None, max_length=25, pattern=NAME_PATTERN)
    content: str | None = None
    description: str | None = Field(None, max_length=100)


@router.get("")
async def prompts_list() -> JSONResponse:
    """GET prompts - list all."""
    try:
        prompts = list_prompts()
        return JSONResponse(content=prompts)
    except Exception as e:
        logger.error(f"Prompts LIST failed: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@router.get("/active")
async def prompts_active() -> JSONResponse:
    """GET the active prompt."""
    try:
        active = get_active_prompt()
        if active:
            return JSONResponse(content={"name": active.name, "id": active.id})
        return JSONResponse(status_code=404, content={"error": "No active prompt found"})
    except Exception as e:
        logger.error(f"Prompts ACTIVE failed: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@router.get("/name/{name}")
async def prompts_get_by_name(name: str) -> JSONResponse:
    """GET prompt by name."""
    try:
        prompt = get_prompt_by_name(name)
        if prompt is None:
            return JSONResponse(status_code=404, content={"error": f"Prompt '{name}' not found"})
        return JSONResponse(
            content={
                "id": prompt.id,
                "name": prompt.name,
                "description": prompt.description,
                "content": prompt.content,
                "is_active": prompt.is_active,
            }
        )
    except Exception as e:
        logger.error(f"Prompts GET_BY_NAME failed: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@router.get("/{prompt_id}")
async def prompts_get_by_id(prompt_id: str) -> JSONResponse:
    """GET prompt by ID."""
    try:
        prompt = get_prompt_by_id(prompt_id)
        if prompt is None:
            return JSONResponse(
                status_code=404, content={"error": f"Prompt '{prompt_id}' not found"}
            )
        return JSONResponse(
            content={
                "id": prompt.id,
                "name": prompt.name,
                "description": prompt.description,
                "content": prompt.content,
                "is_active": prompt.is_active,
            }
        )
    except Exception as e:
        logger.error(f"Prompts GET_BY_ID failed: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@router.put("/{prompt_id}")
async def prompts_update_by_id(prompt_id: str, request: UpdatePromptRequest) -> JSONResponse:
    """PUT prompt by ID."""
    try:
        success = update_prompt(
            prompt_id,
            name=request.name,
            description=request.description,
            content=request.content,
        )
        if not success:
            return JSONResponse(
                status_code=404, content={"error": f"Prompt '{prompt_id}' not found"}
            )
        return JSONResponse(content={"message": f"Prompt '{prompt_id}' updated"})
    except Exception as e:
        logger.error(f"Prompts UPDATE_BY_ID failed: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@router.delete("/{prompt_id}")
async def prompts_delete_by_id(prompt_id: str) -> JSONResponse:
    """Delete a prompt by ID."""
    try:
        prompt = get_prompt_by_id(prompt_id)
        if prompt is None:
            return JSONResponse(
                status_code=404, content={"error": f"Prompt '{prompt_id}' not found"}
            )
        delete_prompt(prompt_id)
        return JSONResponse(content={"message": f"Prompt '{prompt_id}' deleted"})
    except Exception as e:
        logger.error(f"Failed to delete prompt: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@router.post("")
async def prompts_post(request: AddPromptRequest) -> JSONResponse:
    """POST prompts - add a new prompt."""
    try:
        add_prompt(request.name, request.description, request.content)
        return JSONResponse(content={"message": f"Prompt '{request.name}' saved"})
    except Exception as e:
        logger.error(f"Prompts POST failed: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})


@router.post("/activate/{prompt_id}")
async def prompts_activate(prompt_id: str) -> JSONResponse:
    """POST prompts - activate a prompt by ID."""
    try:
        prompt = get_prompt_by_id(prompt_id)
        if not prompt:
            return JSONResponse(
                status_code=404, content={"error": f"Prompt '{prompt_id}' not found"}
            )
        set_active_prompt(prompt_id)
        return JSONResponse(content={"message": f"Prompt '{prompt.name}' activated"})
    except Exception as e:
        logger.error(f"Prompts ACTIVATE failed: {e}")
        return JSONResponse(status_code=500, content={"error": "Internal server error"})
