"""Search endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["search"])


@router.get("/search-rules")
async def search_rules(query: str, limit: int = 10) -> dict:
    """Search for Sigma rules matching the query."""
    return {"data": [], "meta": {"count": 0, "query": query}}
