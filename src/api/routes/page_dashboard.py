from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.presentation import TEMPLATES_DIR

templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix="", tags=["page-dashboard"])


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard/index.html")
