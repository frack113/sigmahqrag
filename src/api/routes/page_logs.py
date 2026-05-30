from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.front import TEMPLATES_DIR
from src.shared import get_config

templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix="", tags=["page-logs"])


@router.get("/logs", response_class=HTMLResponse)
async def logs_explorer(request: Request):
    cfg = get_config().to_dict()
    return templates.TemplateResponse(
        request=request,
        name="logs/index.html",
        context={"config": cfg, "config_json": __import__("json").dumps(cfg)},
    )
