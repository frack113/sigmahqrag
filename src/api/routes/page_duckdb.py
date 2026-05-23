from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.front import TEMPLATES_DIR

templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix="", tags=["page-duckdb"])


@router.get("/duckdb", response_class=HTMLResponse)
async def duckdb_explorer(request: Request):
    return templates.TemplateResponse(request=request, name="duckdb/explorer.html")
