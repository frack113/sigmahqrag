"""Coverage check API."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, status

from src.back.rag.search import SearchEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/coverage", tags=["v1-coverage"])


@router.get("")
async def check_coverage(
    file_path: str = Query(..., description="Path to Sigma rule file"),
) -> dict:
    """Check coverage of a Sigma rule file against indexed rules."""
    if not file_path.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file_path cannot be empty",
        )

    try:
        engine = SearchEngine()
        results = await engine.search(f"coverage analysis for {file_path}", top_k=20)

        # Group results by logsource for coverage overview
        logsource_coverage: dict[str, int] = {}
        for r in results:
            meta = r.get("metadata", {})
            source = meta.get("source", "unknown")
            logsource_coverage[source] = logsource_coverage.get(source, 0) + 1

        return {
            "file_path": file_path,
            "related_rules_found": len(results),
            "logsource_coverage": logsource_coverage,
            "results": results[:10],
        }
    except Exception as e:
        logger.error("Coverage check failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Coverage check failed",
        ) from None
