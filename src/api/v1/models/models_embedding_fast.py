"""FastEmbed model API v1 routes — sparse models (Splade_PP_en_v1, etc.) managed by fastembed."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.config.settings import EMBEDDING_FAST_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/models/embedding-fast", tags=["v1-models-embedding-fast"])


@router.get("/installed")
async def list_installed_fastembed_models() -> JSONResponse:
    """List installed fastembed models from embedding_fast directory."""
    try:
        models_list: list[dict[str, str]] = []
        fast_dir = Path(EMBEDDING_FAST_DIR)
        if fast_dir.exists():
            for entry in fast_dir.iterdir():
                if not entry.is_dir() or entry.name.startswith("."):
                    continue
                repo_id = entry.name
                models_list.append({"repo_id": repo_id})

        return JSONResponse(content={"models": models_list})
    except Exception as e:
        logger.error(f"Failed to list fastembed models: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


@router.get("/progress")
async def get_fastembed_progress() -> JSONResponse:
    """FastEmbed models are managed internally by the fastembed library; progress is not tracked here."""
    return JSONResponse(content={"progress": 100, "status": "completed"})
