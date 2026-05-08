"""Chat page route."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["chat-page"])
templates = Jinja2Templates(directory="src/front/templates")


@router.get("/chat")
async def chat_page(request: Request):
    """Serve the chat page with Jinja2 template."""
    return templates.TemplateResponse(request=request, name="chat.html")
