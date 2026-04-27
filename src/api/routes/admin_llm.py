"""LLM API routes for HuggingFace models."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.api.dependencies import require_role, get_model_manager
from src.auth.models import UserRole
from src.core.services.manager import ModelManager, ModelNotFoundError
from src.core.types import HFRepo
from src.core.services.download import DownloadError

logger = logging.getLogger(__name__)


class DownloadRequest(BaseModel):
    repo_id: str
    filename: str | None = None
    expected_hash: str | None = None


router = APIRouter(prefix="/llm", tags=["llm"])


@router.get("/list-files/{repo_id}")
async def list_model_files(
    repo_id: str, 
    mm: ModelManager = Depends(get_model_manager)
) -> JSONResponse:
    """Get GGUF files for a model repo."""
    try:
        files = mm.download_service.list_gguf_files(HFRepo.from_string(repo_id))
        return JSONResponse(content={"files": files})
    except DownloadError as e:
        logger.error(f"Get files failed: {e}")
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        logger.error(f"Unexpected error listing files: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/download")
async def download_model(
    request: DownloadRequest, 
    mm: ModelManager = Depends(get_model_manager)
) -> JSONResponse:
    """Download a model from HuggingFace."""
    try:
        record = await mm.download_model(
            repo_id=request.repo_id, 
            filename=request.filename, 
            expected_hash=request.expected_hash
        )
        return JSONResponse(content={
            "success": True,
            "repo_id": request.repo_id,
            "path": str(record.local_path),
            "size": record.file_size,
        })
    except DownloadError as e:
        logger.error(f"Download failed: {e}")
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        logger.error(f"Unexpected error during download: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/installed")
async def list_installed_models(
    mm: ModelManager = Depends(get_model_manager)
) -> JSONResponse:
    """List installed models."""
    try:
        models = await mm.list_installed_models()
        return JSONResponse(content={
            "models": [
                {
                    "repo_id": m.repo_id,
                    "path": str(m.local_path),
                    "size": m.file_size,
                    "status": m.status
                } for m in models
            ]
        })
    except Exception as e:
        logger.error(f"List failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.delete("/{repo_id:path}", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def delete_model(
    repo_id: str, 
    mm: ModelManager = Depends(get_model_manager)
) -> JSONResponse:
    """Delete an installed model."""
    try:
        await mm.delete_model(repo_id)
        return JSONResponse(content={"success": True, "repo_id": repo_id})
    except ModelNotFoundError as e:
        logger.error(f"Delete failed: {e}")
        return JSONResponse(status_code=404, content={"error": str(e)})
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
