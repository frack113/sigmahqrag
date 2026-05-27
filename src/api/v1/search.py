"""Search API for Sigma rules."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["v1-search"])


async def search_rules(query: str, limit: int = 10) -> list[str]:
    return []


@router.post("")
async def search_rules_endpoint(
    query: str = Query(..., description="Search query"),
    limit: int = Query(default=10, ge=1, le=100),
) -> JSONResponse:
    """Search Sigma rules by query."""
    try:
        results = await search_rules(query, limit=limit)
        return JSONResponse(content={"rules": results})
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})
