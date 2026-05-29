"""Coverage check API."""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/api/v1/coverage", tags=["v1-coverage"])


@router.get("")
async def check_coverage(
    file_path: str = Query(..., description="Path to Sigma rule file"),
) -> JSONResponse:
    """Check coverage of a Sigma rule file.

    TODO: Implement rule coverage analysis against available log sources.
    """
    return JSONResponse(
        status_code=501,
        content={"error": "Not implemented", "message": "Coverage check is not yet implemented"},
    )
