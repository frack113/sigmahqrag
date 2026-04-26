"""Embedding model API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.api.dependencies import require_role
from src.auth.models import UserRole

logger = logging.getLogger(__name__)


class EmbeddingDownloadRequest(BaseModel):
    """Request to download an embedding model."""
    repo_id: str
    filename: str


router = APIRouter(prefix="/embeddings", tags=["embeddings"])


@router.get("/search")
async def search_embedding_models(query: str, limit: int = 20) -> JSONResponse:
    """Search for embedding models on HuggingFace."""
    try:
        from huggingface_hub import HfApi

        api = HfApi()
        results = api.list_models(search=query, limit=limit)
        models = [{"id": r.id, "title": r.modelId} for r in results if r.id]

        return JSONResponse(content={"models": models})

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/{repo_id}/files")
async def get_embedding_files(repo_id: str) -> JSONResponse:
    """Get files for an embedding model repo."""
    try:
        from huggingface_hub import HfApi

        api = HfApi()
        files = api.list_repo_files(repo_id=repo_id)
        gguf_files = sorted(set(f for f in files if f.endswith(".gguf")))

        return JSONResponse(content={"files": gguf_files})

    except Exception as e:
        logger.error(f"Get files failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/download", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def download_embedding(request: EmbeddingDownloadRequest) -> JSONResponse:
    """Download an embedding model."""
    try:
        from huggingface_hub import hf_hub_download
        from src.config import EMBEDDINGS_DIR

        EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)

        file_path = hf_hub_download(
            repo_id=request.repo_id,
            filename=request.filename,
            cache_dir=str(EMBEDDINGS_DIR / request.repo_id.replace("/", "_")),
            resume_download=True,
        )

        dest = EMBEDDINGS_DIR / request.filename
        dest.write_bytes(open(file_path, "rb").read())

        return JSONResponse(content={
            "success": True,
            "repo_id": request.repo_id,
            "filename": request.filename,
            "path": str(dest),
        })

    except Exception as e:
        logger.error(f"Download failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/installed")
async def list_installed_embeddings() -> JSONResponse:
    """List installed embedding models."""
    try:
        from src.config import EMBEDDINGS_DIR

        if not EMBEDDINGS_DIR.exists():
            return JSONResponse(content={"models": []})

        models = []
        for f in EMBEDDINGS_DIR.iterdir():
            if f.suffix.lower() == ".gguf":
                models.append({
                    "name": f.stem,
                    "path": str(f),
                    "size": f.stat().st_size,
                })

        return JSONResponse(content={"models": models})

    except Exception as e:
        logger.error(f"List failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.delete("/{name}", dependencies=[Depends(require_role(UserRole.ADMIN))])
async def delete_embedding(name: str) -> JSONResponse:
    """Delete an embedding model."""
    try:
        from src.config import EMBEDDINGS_DIR

        model_path = EMBEDDINGS_DIR / f"{name}.gguf"
        if model_path.exists():
            model_path.unlink()
            return JSONResponse(content={"success": True, "name": name})

        return JSONResponse(status_code=404, content={"error": "Model not found"})

    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})