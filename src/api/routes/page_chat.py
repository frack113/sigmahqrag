"""Chat page route."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from src.front import TEMPLATES_DIR

templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix="", tags=["page-chat"])


@router.get("/")
@router.get("/chat")
async def chat_page(request: Request):
    """Serve the chat page with Jinja2 template."""
    prompts = _get_prompts()
    return templates.TemplateResponse(
        request=request,
        name="chat.html",
        context={
            "prompts": prompts,
        },
    )


def _get_prompts() -> list[dict]:
    """Fetch system prompts from the database."""
    try:
        from src.application.system_prompt import list_prompts

        return list_prompts()
    except Exception:
        return []
