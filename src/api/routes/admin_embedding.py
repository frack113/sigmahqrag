"""Embedding model admin API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from src.api.dependencies import get_embedding_manager
from src.core.services.embedding import EmbeddingManager

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/admin/embeddings", tags=["admin-embeddings"])


@router.get("/")
async def embedding_admin_get(
    action: str = Query(..., description="Action: installed, info"),
    repo_id: str | None = Query(None, description="HuggingFace repo ID"),
    manager: EmbeddingManager = Depends(get_embedding_manager),
) -> JSONResponse:
    """Unified embeddings admin GET endpoint."""
    try:
        match action:
            case "installed":
                models = await manager.list_installed()
                return JSONResponse(content={"models": models})

            case "info":
                if not repo_id:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "repo_id required for action=info"},
                    )
                registry = await manager.list_installed()
                if repo_id not in registry:
                    return JSONResponse(
                        status_code=404,
                        content={"error": f"Model {repo_id} not found"},
                    )
                return JSONResponse(content={"model": registry[repo_id]})

            case _:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Unknown action: {action}"},
                )

    except Exception as e:
        logger.error(f"Action {action} failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/")
async def embedding_admin_post(
    action: str = Query(..., description="Action: download, delete"),
    repo_id: str = Query(..., description="HuggingFace repo ID"),
    filename: str | None = Query(None, description="Specific file to download"),
    manager: EmbeddingManager = Depends(get_embedding_manager),
) -> JSONResponse:
    """Unified embeddings admin POST endpoint."""
    try:
        match action:
            case "download":
                record = await manager.download_model(
                    repo_id=repo_id,
                    filename=filename,
                )
                return JSONResponse(content={
                    "success": True,
                    "repo_id": repo_id,
                    "path": str(record.local_path),
                })

            case "delete":
                await manager.delete_model(repo_id)
                return JSONResponse(content={"success": True, "repo_id": repo_id})

            case _:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Unknown action: {action}"},
                )

    except Exception as e:
        logger.error(f"Action {action} failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
