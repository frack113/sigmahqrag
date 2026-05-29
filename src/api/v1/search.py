"""Search API for Sigma rules."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["v1-search"])


@router.post("")
async def search_rules_endpoint(
    query: str = Query(..., description="Search query"),
    limit: int = Query(default=10, ge=1, le=100),
) -> JSONResponse:
    """Search Sigma rules by query.

    TODO: Implement actual search via Qdrant vector or DuckDB full-text.
    """
    return JSONResponse(
        status_code=501,
        content={"error": "Not implemented", "message": "Search is not yet implemented"},
    )
