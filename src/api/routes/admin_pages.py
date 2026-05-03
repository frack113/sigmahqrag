"""Admin page routes for Jinja2 templates."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

from src.services.health_check import HealthCheckService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-pages"])

templates = Jinja2Templates(directory="src/front/templates")

health_service = HealthCheckService()


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


@router.get("/admin/health")
async def admin_health(request: Request) -> HTMLResponse:
    """Serve health check page."""
    return templates.TemplateResponse(request=request, name="admin/health.html")


@router.get("/admin/logs")
async def admin_logs(request: Request) -> HTMLResponse:
    """Serve logs page."""
    return templates.TemplateResponse(request=request, name="admin/logs.html")


@router.get("/admin/hardware")
async def admin_hardware(request: Request) -> HTMLResponse:
    """Serve hardware page."""
    return templates.TemplateResponse(request=request, name="admin/hardware.html")


@router.get("/admin/llama")
async def admin_llama(request: Request) -> HTMLResponse:
    """Serve llama.cpp management page."""
    return templates.TemplateResponse(request=request, name="admin/llama.html")


@router.get("/admin/qdrant")
async def admin_qdrant(request: Request) -> HTMLResponse:
    """Serve Qdrant management page."""
    return templates.TemplateResponse(request=request, name="admin/qdrant.html")


@router.get("/admin/prompts")
async def admin_prompts(request: Request) -> HTMLResponse:
    """Serve prompts management page."""
    return templates.TemplateResponse(request=request, name="admin/prompts.html")
