"""Search endpoint."""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from src.rag.search import SearchEngine, format_search_result, get_citation
from src.schemas.search import SearchRequest, SearchResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["search"])

SEARCH_TIMEOUT = 3.0


class SearchResult(BaseModel):
    """Search result item."""

    title: str = Field(default="")
    description: str = Field(default="")
    text: str = Field(default="")
    score: float = Field(default=0.0)
    citation: str = Field(default="")
    metadata: dict[str, Any] = Field(default_factory=dict)


async def _search_with_timeout(
    query: str,
    limit: int,
) -> list[dict[str, Any]]:
    """Execute search with timeout."""
    engine = SearchEngine(top_k=limit)
    results = await engine.search(query)
    return results


@router.post("/api/search-rules", response_model=SearchResponse)
async def search_rules(request: SearchRequest) -> SearchResponse:
    """Search for Sigma rules matching the query."""
    if not request.query or not request.query.strip():
        return SearchResponse(data=[], meta={"count": 0, "query": "", "error": None})

    try:
        results = await asyncio.wait_for(
            _search_with_timeout(request.query, request.limit),
            timeout=SEARCH_TIMEOUT,
        )

        formatted_results: list[dict[str, Any]] = []
        for result in results:
            formatted = format_search_result(result)
            citation = get_citation(result)
            formatted_results.append(
                {
                    "title": formatted.get("metadata", {}).get("title", ""),
                    "description": formatted.get("metadata", {}).get("description", ""),
                    "text": formatted.get("text", ""),
                    "score": formatted.get("score", 0.0),
                    "citation": citation,
                    "metadata": formatted.get("metadata", {}),
                }
            )

        return SearchResponse(
            data=formatted_results,
            meta={
                "count": len(formatted_results),
                "query": request.query,
                "error": None,
            },
        )

    except TimeoutError:
        logger.error(f"Search timeout after {SEARCH_TIMEOUT}s for query: {request.query}")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Search timeout (>{SEARCH_TIMEOUT}s)",
        ) from None
    except Exception as e:
        logger.error(f"Search error: {e}")
        return SearchResponse(
            data=[],
            meta={"count": 0, "query": request.query, "error": str(e)},
        )


@router.get("/search-rules")
async def search_rules_get(query: str, limit: int = 10) -> SearchResponse:
    """Search for Sigma rules matching the query (GET version)."""
    request = SearchRequest(query=query, limit=limit)
    return await search_rules(request)
