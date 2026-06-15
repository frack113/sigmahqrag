"""Chat page route."""

from __future__ import annotations

import os

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from src.presentation import TEMPLATES_DIR

templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix="", tags=["page-chat"])


@router.get("/")
@router.get("/chat")
async def chat_page(request: Request):
    """Serve the chat page with Jinja2 template."""
    is_setup = request.query_params.get("setup", "").lower() in ("1", "true") or os.environ.get(
        "_SIGMA_SETUP_MODE", ""
    ).lower() in ("1", "true", "yes")
    if is_setup:
        return RedirectResponse(url="/setup")
    prompts = _get_prompts()
    return templates.TemplateResponse(
        request=request,
        name="chat/index.html",
        context={
            "prompts": prompts,
        },
    )


def _get_prompts() -> list[dict]:
    """Fetch system prompts from the database."""
    try:
        from src.application.system.prompts import list_prompts

        return list_prompts()
    except Exception:
        return []
