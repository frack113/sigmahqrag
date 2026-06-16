"""Embedding model API v1 routes."""

from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.api.dependencies import get_database_service, get_embedding_manager, get_unified_registry
from src.api.v1.models._models_shared import (
    _delete_all_models_of_type,
    _download_progress,
)
from src.api.v1.models._models_shared import (
    _delete_embedding_model as _shared_delete_embedding,
)
from src.application.models import EmbeddingManager
from src.config.settings import EMBEDDINGS_DIR, get_config
from src.infrastructure.database import DatabaseService
from src.infrastructure.vectorstore.collections import list_collections

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/models", tags=["v1-models-embedding"])

MODEL_ID_RE = re.compile(r"^[\w.-]+/[\w.-]+$")


@router.get("/embedding/installed")
async def list_installed_embedding_models() -> JSONResponse:
    """List installed embedding models."""
    try:
        db = get_database_service()
        reg = get_unified_registry()
        from src.config.settings import EMBEDDINGS_DIR

        reg.sync_embeddings_folder(EMBEDDINGS_DIR, db)
        embeddings = reg.list_embeddings(db)
        return JSONResponse(content={"models": embeddings})
    except Exception as e:
        logger.error(f"Failed to list installed embedding models: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


@router.get("/embedding/progress")
async def get_embedding_progress(repo_id: str) -> JSONResponse:
    """Get embedding download progress."""
    progress = _download_progress.get(f"emb_{repo_id}", {"progress": 0, "status": "idle"})
    return JSONResponse(content=progress)


@router.post("/embedding/download")
async def download_embedding_model(
    repo_id: str,
    filename: str | None = None,
) -> JSONResponse:
    """Download an embedding model. Auto-deletes existing embedding model first."""
    import asyncio

    _delete_all_models_of_type("embeddings")

    def set_emb_progress(r: str, p: int, s: str = "downloading"):
        _download_progress[f"emb_{r}"] = {"progress": p, "status": s}

    set_emb_progress(repo_id, 0, "starting")

    async def download_in_background():
        try:
            manager = get_embedding_manager()
            set_emb_progress(repo_id, 10, "downloading")
            await manager.download_model(repo_id=repo_id, filename=filename)
            set_emb_progress(repo_id, 100, "completed")
        except Exception as e:
            set_emb_progress(repo_id, 0, f"error: {str(e)}")

    asyncio.create_task(download_in_background())

    return JSONResponse(
        content={
            "success": True,
            "message": "Download started in background",
            "repo_id": repo_id,
        }
    )


@router.delete("/embedding/{repo_id}")
async def delete_embedding_model(repo_id: str) -> JSONResponse:
    """Delete an embedding model."""
    result = _shared_delete_embedding(repo_id)
    if result.get("success"):
        return JSONResponse(content={"success": True, "repo_id": repo_id})

    status_code = result.get("status_code", 500)
    return JSONResponse(status_code=status_code, content={"error": result["error"]})


@router.get("/embeddings/search")
async def search_embedding_models(
    query: str,
    limit: int = 20,
    manager: EmbeddingManager = Depends(get_embedding_manager),
) -> JSONResponse:
    """Search for embedding models on HuggingFace."""
    try:
        results = await manager.search_models(query, limit=limit)
        return JSONResponse(content={"models": [{"repo_id": r.full_id} for r in results]})
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


@router.get("/embeddings/config")
async def get_embedding_config() -> JSONResponse:
    """Get the global embedding model configuration."""
    config = DatabaseService.get_instance().get_embedding_config()
    return JSONResponse(content=json.loads(json.dumps(config, default=str)))


@router.put("/embeddings/config")
async def update_embedding_config(body: dict) -> JSONResponse:
    """Update the global embedding model.

    Sending model="" resets to default.
    Probes the model dimension and detects Qdrant collection mismatch.
    """
    if "model" not in body:
        return JSONResponse(status_code=400, content={"error": "model is required"})

    model = (body.get("model") or "").strip()
    if model and not MODEL_ID_RE.match(model):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid model ID format (expected: org/model)"},
        )

    db = DatabaseService.get_instance()

    if not model:
        db.delete_embedding_config()
        result = json.loads(json.dumps(db.get_embedding_config(), default=str))
        result["dim_mismatch"] = False
        result["model_dimension"] = None
        result["collection_dimension"] = None
        result["mismatched_collections"] = []
        return JSONResponse(content=result)

    # --- probe dimension first ---
    model_dir = EMBEDDINGS_DIR / model
    if not model_dir.exists():
        return JSONResponse(
            status_code=200,
            content={
                "model": model,
                "dim_mismatch": False,
                "model_dimension": None,
                "collection_dimension": None,
                "mismatched_collections": [],
                "warning": f"Model {model} not found on disk. Download it first to enable dimension detection.",
            },
        )

    try:
        dim = await EmbeddingManager._detect_model_dimension(model_dir)
    except Exception as e:
        logger.warning("Could not probe dimension for %s: %s", model, e)
        return JSONResponse(
            status_code=200,
            content={
                "model": model,
                "dim_mismatch": False,
                "model_dimension": None,
                "collection_dimension": None,
                "mismatched_collections": [],
                "warning": f"Failed to detect dimension: {e}",
            },
        )

    # --- check collections ---
    cfg = get_config()
    try:
        collections = await list_collections(cfg.qdrant_host, cfg.qdrant_port)
    except Exception as e:
        logger.warning("Could not list Qdrant collections: %s", e)
        return JSONResponse(
            status_code=200,
            content={
                "model": model,
                "dim_mismatch": False,
                "model_dimension": dim,
                "collection_dimension": None,
                "mismatched_collections": [],
                "warning": f"Qdrant unreachable: {e}",
            },
        )

    # --- everything succeeded, write config ---
    db.set_embedding_config(model)
    cfg.qdrant_vector_size = dim
    cfg.save()

    result = json.loads(json.dumps(db.get_embedding_config(), default=str))
    result["model_dimension"] = dim
    result["collection_dimension"] = collections[0].get("vector_size") if collections else None
    mismatched = [c for c in collections if c.get("vector_size") and c["vector_size"] != dim]
    result["mismatched_collections"] = [c.get("name") for c in mismatched]
    result["dim_mismatch"] = bool(mismatched)

    return JSONResponse(content=result)


@router.get("/embeddings/dimension-status")
async def embedding_dimension_status() -> JSONResponse:
    """Check if the active embedding model dimension matches all Qdrant collections."""
    try:
        db = DatabaseService.get_instance()
        config = db.get_embedding_config()
        model = config.get("model", "")

        if not model:
            return JSONResponse(
                content={
                    "model_dimension": None,
                    "collection_dimension": None,
                    "mismatch": False,
                    "mismatched_collections": [],
                    "error": "No active embedding model",
                }
            )

        cfg = get_config()
        model_dim = cfg.qdrant_vector_size
        collections = await list_collections(cfg.qdrant_host, cfg.qdrant_port)
        coll_dim = collections[0].get("vector_size") if collections else None
        mismatched = [
            c.get("name")
            for c in collections
            if c.get("vector_size") and c["vector_size"] != model_dim
        ]

        return JSONResponse(
            content={
                "model_dimension": model_dim,
                "collection_dimension": coll_dim,
                "mismatch": bool(mismatched),
                "mismatched_collections": mismatched,
            }
        )
    except Exception as e:
        logger.error("Dimension status check failed: %s", e)
        return JSONResponse(
            content={
                "model_dimension": None,
                "collection_dimension": None,
                "mismatch": False,
                "mismatched_collections": [],
                "error": str(e),
            }
        )


@router.get("/embeddings/{repo_id}/files")
async def get_embedding_files(
    repo_id: str, manager: EmbeddingManager = Depends(get_embedding_manager)
) -> JSONResponse:
    """Get files for an embedding model repo."""
    try:
        files = await manager.get_repo_files(repo_id)
        return JSONResponse(content={"files": files})
    except Exception as e:
        logger.error(f"Files failed: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})
