"""Admin model management endpoints."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.api.dependencies import get_database_service, get_unified_registry
from src.api.v1.models._models_shared import _delete_embedding_model, _delete_llm_model_file
from src.config.settings import LLM_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/admin", tags=["admin-models"])


@router.get("/models")
async def get_models() -> JSONResponse:
    """GET /api/v1/admin/models - Return installed models list."""
    try:
        db = get_database_service()
        reg = get_unified_registry()
        reg.sync_llm_folder(LLM_DIR, db)
        llms = reg.list_llms(db)

        model_list = []
        for repo_id, data in llms.items():
            for filename, info in data.get("files", {}).items():
                model_list.append(
                    {
                        "repo_id": repo_id,
                        "filename": info.get("filename", filename),
                        "size_mb": (info.get("file_size", 0) or 0) / (1024 * 1024),
                    }
                )

        return JSONResponse(content={"status": "success", "data": {"models": model_list}})
    except Exception as e:
        logger.error(f"Failed to list models: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "An internal error occurred"},
        )


@router.post("/models/delete")
async def delete_model(request: dict) -> JSONResponse:
    """POST /api/v1/admin/models/delete - Delete a model."""
    repo_id = request.get("repo_id")
    filename = request.get("filename")

    if not repo_id or not filename:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "error": "repo_id and filename required"},
        )

    result = _delete_llm_model_file(repo_id, filename)
    if result.get("success"):
        return JSONResponse(content={"status": "success", "message": result["message"]})

    status_code = result.get("status_code", 500)
    return JSONResponse(
        status_code=status_code,
        content={"status": "error", "error": result["error"]},
    )


@router.post("/models/delete-embedding")
async def delete_embedding_model(request: dict) -> JSONResponse:
    """POST /api/v1/admin/models/delete-embedding - Delete an embedding model."""
    repo_id = request.get("repo_id")

    if not repo_id:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "error": "repo_id required"},
        )

    result = _delete_embedding_model(repo_id)
    if result.get("success"):
        return JSONResponse(content={"status": "success", "message": result["message"]})

    status_code = result.get("status_code", 500)
    return JSONResponse(
        status_code=status_code,
        content={"status": "error", "error": result["error"]},
    )
