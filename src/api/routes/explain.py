"""Endpoint for explaining a Sigma rule."""

import logging

import httpx
from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter(tags=["explain"])


@router.post("/explain-rule")
async def explain_rule(rule_id: str, text: str) -> dict:
    """Explain a Sigma rule using the backend service."""
    if not rule_id or not text:
        raise HTTPException(status_code=400, detail="Rule ID and text are required")

    url = "http://localhost:8080/v1/rule-explain"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json={"rule_id": rule_id, "text": text})

            if response.status_code == 200:
                result = response.json()
                title = result.get("metadata", {}).get("title", "Unknown")
                return {
                    "rule_id": rule_id,
                    "title": title,
                    "text": text,
                }
            else:
                raise HTTPException(
                    status_code=response.status_code, detail="Backend returned error"
                )
    except Exception as e:
        logger.error(f"Explain error: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e
