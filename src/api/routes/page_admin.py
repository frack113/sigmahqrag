"""Admin page routes for Jinja2 templates."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from src.config.settings import get_config
from src.presentation import TEMPLATES_DIR

templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter(prefix="", tags=["page-admin"])

_BINARY_NAMES: dict[str, tuple[str, ...]] = {
    "llama": ("llama-server.exe", "llama-server")
    if sys.platform == "win32"
    else ("llama-server", "llama-server.exe"),
    "qdrant": ("qdrant.exe", "qdrant") if sys.platform == "win32" else ("qdrant", "qdrant.exe"),
}


async def _needs_setup() -> bool:
    """Check if any internal service binary is missing — first-run detection."""
    cfg = get_config()
    for service in ("llama", "qdrant"):
        if cfg.service_is_internal(service):
            bin_dir = getattr(cfg, f"{service}_binary_path", "")
            if not bin_dir.strip():
                return True
            binary_path = Path(bin_dir).resolve()
            names = _BINARY_NAMES.get(service, (service,))
            found = False
            for name in names:
                candidate = binary_path if binary_path.name == name else binary_path / name
                if await asyncio.to_thread(candidate.exists):
                    found = True
                    break
            if not found:
                return True
    return False


@router.get("/config")
@router.get("/config/")
async def config_page(request: Request):
    """Serve the unified config dashboard page."""
    # Skip redirect for HTMX partial requests to avoid full-page injection
    if not request.headers.get("HX-Request") and await _needs_setup():
        return RedirectResponse(url="/setup", status_code=302)
    cfg = get_config().to_dict()
    return templates.TemplateResponse(
        request=request,
        name="config/config.html",
        context={"config": cfg, "config_json": json.dumps(cfg)},
    )


# Legacy redirects for backward compatibility
@router.get("/config/system")
@router.get("/config/system/")
async def config_system_redirect(request: Request):
    """Redirect to unified config page."""
    return RedirectResponse(url="/config", status_code=302)


@router.get("/config/backend")
@router.get("/config/backend/")
async def config_backend_redirect(request: Request):
    """Redirect to unified config page."""
    return RedirectResponse(url="/config", status_code=302)


@router.get("/config/llm")
@router.get("/config/llm/")
async def config_llm_redirect(request: Request):
    """Redirect to unified config page."""
    return RedirectResponse(url="/config", status_code=302)
