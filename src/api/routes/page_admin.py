"""Admin page routes for Jinja2 templates."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from src.config.settings import get_config
from src.presentation import TEMPLATES_DIR

templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix="", tags=["page-admin"])


@router.get("/config/system")
@router.get("/config/system/")
async def config_system_page(request: Request):
    """Serve the config system page (Configuration + Data + Logs)."""
    cfg = get_config().to_dict()
    return templates.TemplateResponse(
        request=request,
        name="config/system.html",
        context={"config": cfg, "config_json": __import__("json").dumps(cfg)},
    )


@router.get("/config/backend")
@router.get("/config/backend/")
async def config_backend_page(request: Request):
    """Serve the config backend page (llama.cpp + Qdrant)."""
    cfg = get_config().to_dict()
    return templates.TemplateResponse(
        request=request,
        name="config/backend.html",
        context={"config": cfg, "config_json": __import__("json").dumps(cfg)},
    )


@router.get("/config/llm")
@router.get("/config/llm/")
async def config_llm_page(request: Request):
    """Serve the config LLM page (LLM + Embedding)."""
    cfg = get_config().to_dict()
    return templates.TemplateResponse(
        request=request,
        name="config/llm.html",
        context={"config": cfg, "config_json": __import__("json").dumps(cfg)},
    )
