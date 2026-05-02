"""Explain endpoint."""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.rag.search import SearchEngine

logger = logging.getLogger(__name__)

router = APIRouter(tags=["explain"])


class ExplainRequest(BaseModel):
    """Explain request."""

    rule_id: str


class ExplainResponse(BaseModel):
    """Explain response."""

    explanation: str
    rule_id: str


@router.get("/explain-rule")
async def explain_rule(rule_id: str) -> dict:
    """Explain a Sigma rule."""
    try:
        engine = SearchEngine()
        results = await engine.search(f"id:{rule_id}", top_k=1)
        
        if not results:
            return {"error": "Rule not found", "rule_id": rule_id}
        
        result = results[0]
        text = result.get("text", "")
        title = result.get("metadata", {}).get("title", "Unknown")
        
        return {
            "rule_id": rule_id,
            "title": title,
            "text": text,
        }
    except Exception as e:
        logger.error(f"Explain error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
