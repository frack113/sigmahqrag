"""Setup page routes."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from src.config.settings import get_config
from src.presentation import TEMPLATES_DIR

templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix="", tags=["page-setup"])


@router.get("/setup")
@router.get("/setup/")
async def setup_wizard(request: Request):
    """Serve the initial setup wizard page."""
    try:
        cfg = get_config().to_dict()
    except Exception:
        cfg = {}
    return templates.TemplateResponse(
        request=request,
        name="setup.html",
        context={"config_json": json.dumps(cfg)},
    )
