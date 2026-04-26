"""LLM API routes for HuggingFace models."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from huggingface_hub import HfApi, hf_hub_download

from src.api.dependencies import require_role
from src.auth.models import UserRole
from src.config import LLM_DIR
from src.core.services import ModelManager

logger = logging.getLogger(__name__)


class DownloadRequest(BaseModel):
    repo_id: str
    filename: str


router = APIRouter(prefix="/llm", tags=["llm"])


# @router.get("/search")
# async def search_models(query: str, limit: int = 20) -> JSONResponse:
#     """Search GGUF models on HuggingFace."""
#     try:
#         api = HfApi()
#         results = api.list_models(apps="llama.cpp", search=query, limit=limit)
#         models = [{"id": r.id, "title": r.modelId} for r in results if r.id]
#         return JSONResponse(content={"models": models})
#     except Exception as e:
#         logger.error(f"Search failed: {e}")
#         return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/list")
async def list_model_files(repo_id: str) -> JSONResponse:
    """Get GGUF files for a model repo."""
    try:
        api = HfApi()
        files = api.list_repo_files(repo_id=repo_id)
        gguf_files = sorted(set(f for f in files if f.endswith(".gguf")))
        return JSONResponse(content={"files": gguf_files})
    except Exception as e:
        logger.error(f"Get files failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/download")
async def download_model(request: DownloadRequest) -> JSONResponse:
    """Download a model from HuggingFace to models/llm/{org}/{model_name}/."""
    try:
        parts = request.repo_id.split("/")
        org, model_name = parts[0], parts[1]
        target_dir = LLM_DIR / org / model_name

        file_path = hf_hub_download(
            repo_id=request.repo_id,
            filename=request.filename,
            local_dir=str(target_dir),
            local_dir_use_symlinks=False,
        )

        return JSONResponse(content={
            "success": True,
            "repo_id": request.repo_id,
            "filename": request.filename,
            "path": file_path,
        })
    except Exception as e:
        logger.error(f"Download failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/installed")
async def list_installed_models() -> JSONResponse:
    """List installed models."""
    try:
        files = []
        if LLM_DIR.exists():
            for f in LLM_DIR.rglob("*.gguf"):
                parts = f.relative_to(LLM_DIR).parts
                depth = len(parts)
                if depth == 3:
                    repo_id = f"{parts[0]}/{parts[1]}"
                elif depth == 1:
                    repo_id = f.parent.name
                else:
                    repo_id = parts[0]
                files.append({
                    "repo_id": repo_id,
                    "path": str(f),
                    "size": f.stat().st_size,
                    "status": "ready"
                })
        return JSONResponse(content={"models": files})
    except Exception as e:
        logger.error(f"List failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.delete("/{repo_id:path}", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def delete_model(repo_id: str) -> JSONResponse:
    """Delete an installed model."""
    try:
        mm = ModelManager()
        await mm.delete_model(repo_id)
        return JSONResponse(content={"success": True, "repo_id": repo_id})
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})