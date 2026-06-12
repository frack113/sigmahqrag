"""Admin page routes for Jinja2 templates."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from src.application.system.health import HealthCheckService
from src.config.settings import get_config
from src.presentation import TEMPLATES_DIR

templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix="", tags=["page-admin"])

health_service = HealthCheckService()


@router.get("/admin")
async def admin_dashboard(request: Request) -> RedirectResponse:
    """Redirect admin root to backend page."""
    return RedirectResponse(url="/admin/backend")


@router.get("/admin/backend")
async def admin_backend(request: Request) -> HTMLResponse:
    """Serve admin backend page."""
    cfg = get_config().to_dict()
    return templates.TemplateResponse(
        request=request,
        name="admin/backend.html",
        context={"config": cfg, "config_json": json.dumps(cfg)},
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
async def admin_logs(request: Request) -> RedirectResponse:
    """Redirect to new logs tab."""
    return RedirectResponse(url="/logs")


@router.get("/admin/llama")
async def admin_llama(request: Request) -> HTMLResponse:
    """Serve llama.cpp management page."""
    cfg = get_config().to_dict()
    return templates.TemplateResponse(
        request=request,
        name="admin/llama.html",
        context={"config": cfg, "config_json": json.dumps(cfg)},
    )


@router.get("/admin/qdrant")
async def admin_qdrant(request: Request) -> HTMLResponse:
    """Serve Qdrant management page."""
    return templates.TemplateResponse(request=request, name="admin/qdrant.html")


@router.get("/admin/system-prompts")
async def admin_prompts(request: Request) -> HTMLResponse:
    """Serve system prompts management page."""
    return templates.TemplateResponse(request=request, name="admin/system_prompts.html")
