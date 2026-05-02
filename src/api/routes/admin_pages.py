"""Admin page routes for Jinja2 templates."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-pages"])

templates = Jinja2Templates(directory="src/templates")


@router.get("/admin")
async def admin_dashboard(request: Request) -> HTMLResponse:
    """Serve admin dashboard page."""
    return templates.TemplateResponse(request=request, name="admin/dashboard.html")


@router.get("/admin/models")
async def admin_models(request: Request) -> HTMLResponse:
    """Serve models management page."""
    return templates.TemplateResponse(request=request, name="admin/models.html")


@router.get("/admin/settings")
async def admin_settings(request: Request) -> HTMLResponse:
    """Serve settings page."""
    return templates.TemplateResponse(request=request, name="admin/settings.html")
