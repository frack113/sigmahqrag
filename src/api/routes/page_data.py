"""Data page routes."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from src.presentation import TEMPLATES_DIR

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


@router.get("/data/sigma-spec")
async def data_sigma_spec_page(request: Request):
    """Serve the Sigma Specification management page."""
    return templates.TemplateResponse(request=request, name="data/sigma_spec.html")


@router.get("/data/vectordb")
async def data_vectordb_page(request: Request):
    """Serve the Vector DB status page."""
    return templates.TemplateResponse(request=request, name="data/vectordb.html")


@router.get("/data/local")
async def data_local_page(request: Request):
    """Serve the Local Files management page."""
    return templates.TemplateResponse(request=request, name="data/local.html")
