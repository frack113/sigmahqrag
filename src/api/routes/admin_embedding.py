"""Embedding model admin API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.api.dependencies import require_role, get_embedding_manager
from src.auth.models import UserRole
from src.core.services.embedding import EmbeddingManager


logger = logging.getLogger(__name__)


class EmbeddingDownloadRequest(BaseModel):
    """Request to download an embedding model."""
    repo_id: str
    filename: str


router = APIRouter(prefix="/embeddings/admin", tags=["embeddings-admin"])


@router.post("/download", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def download_embedding(
    request: EmbeddingDownloadRequest, 
    manager: EmbeddingManager = Depends(get_embedding_manager)
) -> JSONResponse:
    """Download an embedding model."""
    try:
        record = await manager.download_model(
            repo_id=request.repo_id, 
            filename=request.filename
        )
        return JSONResponse(content={
            "success": True,
            "repo_id": request.repo_id,
            "filename": request.filename,
            "path": str(record.local_path),
        })
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.delete("/{repo_id}", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def delete_embedding(
    repo_id: str, 
    manager: EmbeddingManager = Depends(get_embedding_manager)
) -> JSONResponse:
    """Delete an embedding model."""
    try:
        await manager.delete_model(repo_id)
        return JSONResponse(content={"success": True, "repo_id": repo_id})
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
