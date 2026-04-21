"""Coverage check endpoint."""

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["coverage"])


@router.get("/check-coverage")
async def check_coverage(file_path: str) -> dict:
    """Check coverage of a Sigma rule file."""
    raise HTTPException(status_code=501, detail="Not implemented")
