"""Setup page routes — redirects to the unified config dashboard."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

router = APIRouter(prefix="", tags=["page-setup"])


@router.get("/setup")
@router.get("/setup/")
async def setup_wizard(request: Request):
    """Redirect to the unified config dashboard."""
    return RedirectResponse(url="/config", status_code=301)
