"""Embeddings API v1."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.api.dependencies import get_embedding_manager
from src.back.models import EmbeddingManager

logger = logging.getLogger(__name__)


class EmbeddingEmbedRequest(BaseModel):
    """Request to generate embeddings."""

    text: list[str]
    model_name: str | None = None


router = APIRouter(prefix="/api/v1/embeddings", tags=["v1-embeddings"])


@router.post("/embed")
async def embed_text(
    request: EmbeddingEmbedRequest,
    manager: EmbeddingManager = Depends(get_embedding_manager),
) -> JSONResponse:
    """Generate embeddings for the provided text."""
    try:
        embeddings = await manager.embed_text(request.text, request.model_name)
        return JSONResponse(content={"embeddings": embeddings})
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})
