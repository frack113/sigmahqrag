"""Explain endpoint."""

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["explain"])


@router.get("/explain-rule")
async def explain_rule(rule_id: str) -> dict:
    """Explain a Sigma rule."""
    raise HTTPException(status_code=501, detail="Not implemented")
