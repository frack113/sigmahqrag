"""Explain API for Sigma rules."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/explain", tags=["v1-explain"])


@router.post("/rule")
async def explain_rule(
    rule_id: str = Query(..., description="Rule ID"),
    text: str = Query(..., description="Rule text"),
) -> JSONResponse:
    """Explain a Sigma rule using the backend service.

    Args:
        rule_id: Rule identifier
        text: Sigma rule content

    Returns:
        JSON with rule explanation
    """
    if not rule_id or not text:
        return JSONResponse(
            status_code=400,
            content={"error": "Rule ID and text are required"},
        )

    url = "http://localhost:8080/v1/rule-explain"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json={"rule_id": rule_id, "text": text})

            if response.status_code == 200:
                result = response.json()
                title = result.get("metadata", {}).get("title", "Unknown")
                return JSONResponse(
                    content={
                        "rule_id": rule_id,
                        "title": title,
                        "text": text,
                    }
                )
            else:
                return JSONResponse(
                    status_code=response.status_code,
                    content={"error": "Backend returned error"},
                )
    except Exception as e:
        logger.error(f"Explain error: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})
