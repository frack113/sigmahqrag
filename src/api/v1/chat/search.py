"""Search API for Sigma rules."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from src.core.search.engine import SearchEngine
from src.api.v1.chat.schemas import SearchRequest, SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["v1-search"])


@router.post("", response_model=SearchResponse)
async def search_rules_endpoint(
    request: SearchRequest,
) -> SearchResponse:
    """Search Sigma rules by query."""
    if not request.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty",
        )

    try:
        clean_query = request.query.replace("`", "").rstrip("?").strip()
        engine = SearchEngine(use_router=request.use_router)
        results = await engine.search(clean_query, top_k=request.limit)
        return SearchResponse(
            data=results,
            meta={"total": len(results), "query": request.query, "routed": request.use_router},
        )
    except Exception as e:
        logger.error("Search failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed",
        ) from None
