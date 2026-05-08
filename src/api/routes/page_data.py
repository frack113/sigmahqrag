"""Data page routes."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter(prefix="", tags=["pages"])
templates = Jinja2Templates(directory="src/front/templates")


@router.get("/data")
async def data_page(request: Request):
    """Serve the data sources page."""
    return templates.TemplateResponse(request=request, name="data/index.html")


@router.get("/data/github")
async def data_github_page(request: Request):
    """Serve the GitHub data source page."""
    return templates.TemplateResponse(request=request, name="data/github.html")
