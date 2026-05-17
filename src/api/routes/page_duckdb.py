from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["duckdb-pages"])

templates = Jinja2Templates(directory="src/front/templates")


@router.get("/duckdb", response_class=HTMLResponse)
async def duckdb_explorer(request: Request):
    return templates.TemplateResponse(request=request, name="duckdb/explorer.html")
