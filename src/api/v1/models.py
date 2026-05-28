"""Model API v1 routes for managing local LLM and embedding model files."""

from __future__ import annotations

import json
import logging
import re

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.api.dependencies import get_database_service, get_embedding_manager, get_unified_registry
from src.back.database import DatabaseService
from src.back.models import EmbeddingManager, HFRepo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/models", tags=["v1-models"])

# Global download progress tracker
_download_progress = {}


def set_progress(repo_id: str, progress: int, status: str = "downloading"):
    """Track download progress."""
    _download_progress[repo_id] = {"progress": progress, "status": status}


@router.get("/llm/progress")
async def get_download_progress(repo_id: str) -> JSONResponse:
    """Get download progress for a model."""
    progress = _download_progress.get(repo_id, {"progress": 0, "status": "idle"})
    return JSONResponse(content=progress)


# ============= LLM Models =============


@router.get("/llm/installed")
async def list_installed_llm_models() -> JSONResponse:
    """List installed LLM models."""
    try:
        db = get_database_service()
        reg = get_unified_registry()
        from src.shared import LLM_DIR

        reg.sync_llm_folder(LLM_DIR, db)
        llms = reg.list_llms(db)
        models = []
        for repo_id, data in llms.items():
            files = []
            for name, info in data.get("files", {}).items():
                files.append(
                    {
                        "filename": info.get("filename", name),
                        "path": info.get("local_path", ""),
                        "size": info.get("file_size", 0),
                        "status": info.get("status", "ready"),
                    }
                )
            models.append(
                {
                    "repo_id": repo_id,
                    "files": files,
                }
            )
        return JSONResponse(content={"models": models})
    except Exception as e:
        logger.error(f"Failed to list installed LLM models: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


@router.get("/llm/files")
async def list_llm_model_files(repo_id: str | None = None) -> JSONResponse:
    """List available GGUF files for a LLM model."""
    if not repo_id:
        return JSONResponse(status_code=400, content={"error": "repo_id is required"})

    try:
        from src.api.dependencies import get_embedding_manager

        mm = get_embedding_manager()
        files = mm.download_service.list_gguf_files(HFRepo.from_string(repo_id))
        return JSONResponse(content={"files": files})
    except Exception as e:
        logger.error(f"Failed to list files for {repo_id}: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


@router.get("/llm/{repo_id}/info")
async def get_llm_model_info(repo_id: str) -> JSONResponse:
    """Get detailed information about a LLM model."""
    try:
        from src.api.dependencies import get_embedding_manager

        mm = get_embedding_manager()
        info = await mm.get_model_info(repo_id)
        if not info:
            return JSONResponse(
                status_code=404,
                content={"error": f"Model {repo_id} not found"},
            )

        def to_iso(val):
            if val is None:
                return None
            if hasattr(val, "isoformat"):
                return val.isoformat()
            return str(val)

        siblings = []
        if info.siblings:
            for f in info.siblings:
                if f.rfilename.endswith(".gguf"):
                    size = f.size if f.size is not None else 0
                    siblings.append(
                        {
                            "filename": f.rfilename,
                            "size": size,
                        }
                    )

        return JSONResponse(
            content={
                "repo_id": repo_id,
                "id": info.id,
                "author": info.author,
                "sha": info.sha,
                "last_modified": to_iso(info.last_modified),
                "tags": list(info.tags) if info.tags else [],
                "siblings": siblings,
            }
        )
    except Exception as e:
        logger.error(f"Failed to get info for {repo_id}: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


@router.post("/llm/download")
async def download_llm_model(
    repo_id: str,
    filename: str | None = None,
    expected_hash: str | None = None,
) -> JSONResponse:
    """Download a LLM model from HuggingFace. Returns immediately - download runs in background."""
    import asyncio

    from src.api.dependencies import get_embedding_manager

    set_progress(repo_id, 0, "starting")

    async def download_in_background():
        try:
            mm = get_embedding_manager()
            set_progress(repo_id, 5, "downloading")
            await mm.download_model(
                repo_id=repo_id,
                filename=filename,
                expected_hash=expected_hash,
            )
            set_progress(repo_id, 100, "completed")
            logger.info(f"Download completed: {repo_id}")
        except Exception as e:
            set_progress(repo_id, 0, f"error: {str(e)}")
            logger.error(f"Download failed: {e}")

    # Start download in background and return immediately
    asyncio.create_task(download_in_background())

    return JSONResponse(
        content={
            "success": True,
            "message": "Download started in background",
            "repo_id": repo_id,
        }
    )


@router.delete("/llm/{repo_id}")
async def delete_llm_model(repo_id: str) -> JSONResponse:
    """Delete a LLM model entry."""
    try:
        db = get_database_service()
        reg = get_unified_registry()
        record = reg.get_llm(repo_id, db)
        if not record:
            return JSONResponse(status_code=404, content={"error": f"Model {repo_id} not found"})
        reg.remove_llm(repo_id, db)
        return JSONResponse(content={"success": True, "repo_id": repo_id})
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


@router.delete("/llm/{repo_id}/file/{filename}")
async def delete_llm_model_file(repo_id: str, filename: str) -> JSONResponse:
    """Delete a LLM model file."""
    from pathlib import Path

    from src.back.models.exceptions import ModelNotFoundError
    from src.shared import LLM_DIR

    # Validate repo_id to prevent path traversal (format: org/name, e.g. "TheBloke/Mistral-7B")
    if (
        not repo_id
        or ".." in repo_id
        or repo_id.count("/") != 1
        or repo_id.startswith("/")
        or repo_id.endswith("/")
    ):
        return JSONResponse(status_code=400, content={"error": "Invalid repo_id"})

    try:
        db = get_database_service()
        reg = get_unified_registry()
        record = reg.get_llm(repo_id, db)
        if not record:
            raise ModelNotFoundError(f"Model {repo_id} not found")
        if filename not in record.get("files", {}):
            raise ModelNotFoundError(f"File {filename} not found in {repo_id}")
        path = Path(record["files"][filename]["local_path"]).resolve()
        try:
            path.relative_to(Path(LLM_DIR).resolve())
        except ValueError:
            raise ModelNotFoundError(f"Invalid file path for {filename}")
        if path.exists():
            path.unlink()
            # Clean up empty parent directories
            parent = path.parent
            while (
                parent != Path(LLM_DIR).resolve() and parent.exists() and not any(parent.iterdir())
            ):
                parent.rmdir()
                parent = parent.parent
        del record["files"][filename]
        if record["files"]:
            reg._save(db)
        else:
            reg.remove_llm(repo_id, db)
        return JSONResponse(content={"success": True, "repo_id": repo_id, "filename": filename})
    except ModelNotFoundError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


# ============= Embedding Models =============


@router.get("/embedding/installed")
async def list_installed_embedding_models() -> JSONResponse:
    """List installed embedding models."""
    try:
        db = get_database_service()
        reg = get_unified_registry()
        from src.shared import EMBEDDINGS_DIR

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
    """Download an embedding model from HuggingFace."""
    import asyncio

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
    import shutil
    from pathlib import Path

    from src.shared import EMBEDDINGS_DIR

    # Validate repo_id to prevent path traversal
    if not repo_id or ".." in repo_id or "/" in repo_id:
        return JSONResponse(status_code=400, content={"error": "Invalid repo_id"})

    try:
        db = get_database_service()
        reg = get_unified_registry()
        record = reg.get_embedding(repo_id, db)
        if not record:
            return JSONResponse(status_code=404, content={"error": f"Model {repo_id} not found"})
        path = Path(record.get("local_path", "")).resolve()
        try:
            path.relative_to(Path(EMBEDDINGS_DIR).resolve())
        except ValueError:
            return JSONResponse(
                status_code=400, content={"error": f"Invalid path for model {repo_id}"}
            )
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        reg.remove_embedding(repo_id, db)
        return JSONResponse(content={"success": True, "repo_id": repo_id})
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


@router.get("/embeddings/search")
async def search_embedding_models(
    query: str,
    limit: int = 20,
    manager: EmbeddingManager = Depends(get_embedding_manager),
) -> JSONResponse:
    """Search for embedding models on HuggingFace."""
    try:
        results = await manager.search_models(query, limit=limit)
        return JSONResponse(content={"models": results})
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


# ============= Embedding Config (single global model) =============
MODEL_ID_RE = re.compile(r"^[\w.-]+/[\w.-]+$")


@router.get("/embeddings/config")
async def get_embedding_config() -> JSONResponse:
    """Get the global embedding model configuration."""
    config = DatabaseService.get_instance().get_embedding_config()
    return JSONResponse(content=json.loads(json.dumps(config, default=str)))


@router.put("/embeddings/config")
async def update_embedding_config(body: dict) -> JSONResponse:
    """Update the global embedding model.

    Sending model="" resets to default.
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
    if model:
        db.set_embedding_config(model)
    else:
        db.delete_embedding_config()
    config = db.get_embedding_config()
    return JSONResponse(content=json.loads(json.dumps(config, default=str)))


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
