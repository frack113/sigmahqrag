"""Data page routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from src.back.embedding_config import EmbeddingTypeConfig
from src.back.models import EmbeddingManager
from src.front import TEMPLATES_DIR

templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix="", tags=["page-data"])


@router.get("/data")
async def data_page(request: Request):
    """Serve the data sources page."""
    return templates.TemplateResponse(request=request, name="data/overview.html")


@router.get("/data/github")
async def data_github_page(request: Request):
    """Serve the GitHub data source page."""
    return templates.TemplateResponse(request=request, name="data/github.html")


@router.get("/data/embedding")
async def data_embedding_page(request: Request):
    """Serve the embedding configuration page."""
    config_mgr = EmbeddingTypeConfig()
    config = config_mgr.load()

    # Get installed embedding models
    manager = EmbeddingManager()
    installed = await manager.list_installed()
    models = sorted(installed.keys()) if installed else []

    return templates.TemplateResponse(
        request=request,
        name="data/embedding.html",
        context={"config": config, "models": models},
    )


@router.get("/data/vectordb")
async def data_vectordb_page(request: Request):
    """Serve the Vector DB status page."""
    return templates.TemplateResponse(request=request, name="data/vectordb.html")


@router.get("/data/local")
async def data_local_page(request: Request):
    """Serve the Local Files management page."""
    return templates.TemplateResponse(request=request, name="data/local.html")
