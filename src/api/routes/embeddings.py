"""Embedding model API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.api.dependencies import require_role, get_embedding_manager
from src.auth.models import UserRole
from src.core.services.embedding import EmbeddingManager


logger = logging.getLogger(__name__)


class EmbeddingEmbedRequest(BaseModel):
    """Request to generate embeddings."""
    text: list[str]
    model_name: str | None = None


router = APIRouter(prefix="/embeddings", tags=["embeddings"])


@router.get("/search")
async def search_embedding_models(
    query: str, 
    limit: int = 20, 
    manager: EmbeddingManager = Depends(get_embedding_manager)
) -> JSONResponse:
    """Search for embedding models on HuggingFace."""
    try:
        results = await manager.search_models(query, limit=limit)
        return JSONResponse(content={"models": results})
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/{repo_id}/files")
async def get_embedding_files(
    repo_id: str, 
    manager: EmbeddingManager = Depends(get_embedding_manager)
) -> JSONResponse:
    """Get files for an embedding model repo."""
    try:
        # This assumes manager.get_repo_files exists or we use HfApi directly if needed
        # For now, let's keep it simple and see if the manager can handle it
        files = await manager.get_repo_files(repo_id)
        return JSONResponse(content={"files": files})
    except Exception as e:
        logger.error(f"Get files failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/installed")
async def list_installed_embeddings(
    manager: EmbeddingManager = Depends(get_embedding_manager)
) -> JSONResponse:
    """List installed embedding models."""
    try:
        models = await manager.list_installed()
        return JSONResponse(content={"models": models})
    except Exception as e:
        logger.error(f"List failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/embed")
async def embed_text(
    request: EmbeddingEmbedRequest,
    manager: EmbeddingManager = Depends(get_embedding_manager)
) -> JSONResponse:
    """Generate embeddings for the provided text."""
    try:
        embeddings = await manager.embed_text(request.text, request.model_name)
        return JSONResponse(content={"embeddings": embeddings})
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
