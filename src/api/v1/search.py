"""Search API for Sigma rules."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, status

from src.rag.search import SearchEngine
from src.shared.schemas.search import SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/search", tags=["v1-search"])


@router.post("", response_model=SearchResponse)
async def search_rules_endpoint(
    query: str = Query(..., description="Search query"),
    limit: int = Query(default=10, ge=1, le=100),
    use_router: bool = Query(default=False, description="Enable LLM query routing"),
) -> SearchResponse:
    """Search Sigma rules by query."""
    if not query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query cannot be empty",
        )

    try:
        engine = SearchEngine(use_router=use_router)
        results = await engine.search(query, top_k=limit)
        return SearchResponse(
            data=results,
            meta={"total": len(results), "query": query, "routed": use_router},
        )
    except Exception as e:
        logger.error("Search failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Search failed",
        ) from None
