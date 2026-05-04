"""Admin page routes for Jinja2 templates."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.config import load_config
from src.core.backend.services.health_check import HealthCheckService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin-pages"])

templates = Jinja2Templates(directory="src/front/templates")

health_service = HealthCheckService()


@router.get("/admin")
async def admin_dashboard(request: Request) -> HTMLResponse:
    """Serve admin backend page."""
    return templates.TemplateResponse(
        request=request, name="admin/backend.html", context={"config": load_config()}
    )


@router.get("/admin/models")
async def admin_models(request: Request) -> HTMLResponse:
    """Serve models management page."""
    return templates.TemplateResponse(request=request, name="admin/models.html")


@router.get("/admin/health")
async def admin_health(request: Request) -> HTMLResponse:
    """Serve health check page."""
    return templates.TemplateResponse(request=request, name="admin/health.html")


@router.get("/admin/logs")
async def admin_logs(request: Request) -> HTMLResponse:
    """Serve logs page."""
    return templates.TemplateResponse(request=request, name="admin/logs.html")


@router.get("/admin/llama")
async def admin_llama(request: Request) -> HTMLResponse:
    """Serve llama.cpp management page."""
    return templates.TemplateResponse(
        request=request, name="admin/llama.html", context={"config": load_config()}
    )


@router.get("/admin/qdrant")
async def admin_qdrant(request: Request) -> HTMLResponse:
    """Serve Qdrant management page."""
    return templates.TemplateResponse(request=request, name="admin/qdrant.html")


@router.get("/admin/prompts")
async def admin_prompts(request: Request) -> HTMLResponse:
    """Serve prompts management page."""
    return templates.TemplateResponse(request=request, name="admin/prompts.html")
