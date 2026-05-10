"""Model API v1 routes for managing local LLM and embedding model files."""

from __future__ import annotations

import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.back.models import HFRepo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/model", tags=["v1-model"])

# Global download progress tracker
_download_progress = {}


def set_progress(repo_id: str, progress: int, status: str = "downloading"):
    """Track download progress."""
    _download_progress[repo_id] = {"progress": progress, "status": status}


@router.get("/llm/progress/{repo_id}")
async def get_download_progress(repo_id: str) -> JSONResponse:
    """Get download progress for a model."""
    progress = _download_progress.get(repo_id, {"progress": 0, "status": "idle"})
    return JSONResponse(content=progress)


# ============= LLM Models =============


@router.get("/llm/installed")
async def list_installed_llm_models() -> JSONResponse:
    """List installed LLM models."""
    from src.api.dependencies import get_unified_registry

    try:
        reg = get_unified_registry()
        from src.shared import LLM_DIR

        reg.sync_llm_folder(LLM_DIR)
        llms = reg.list_llms()
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
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/llm/files")
async def list_llm_model_files(repo_id: str = None) -> JSONResponse:
    """List available GGUF files for a LLM model."""
    from src.api.dependencies import get_model_manager

    if not repo_id:
        return JSONResponse(status_code=400, content={"error": "repo_id is required"})

    try:
        mm = get_model_manager()
        files = mm.download_service.list_gguf_files(HFRepo.from_string(repo_id))
        return JSONResponse(content={"files": files})
    except Exception as e:
        logger.error(f"Failed to list files for {repo_id}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/llm/{repo_id}/info")
async def get_llm_model_info(repo_id: str) -> JSONResponse:
    """Get detailed information about a LLM model."""
    from src.api.dependencies import get_model_manager

    try:
        mm = get_model_manager()
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
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/llm/download")
async def download_llm_model(
    repo_id: str,
    filename: str | None = None,
    expected_hash: str | None = None,
) -> JSONResponse:
    """Download a LLM model from HuggingFace. Returns immediately - download runs in background."""
    import asyncio

    from src.api.dependencies import get_model_manager

    set_progress(repo_id, 0, "starting")

    async def download_in_background():
        try:
            mm = get_model_manager()
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


@router.delete("/llm/{repo_id}/file/{filename}")
async def delete_llm_model_file(repo_id: str, filename: str) -> JSONResponse:
    """Delete a LLM model file."""
    from pathlib import Path

    from src.api.dependencies import get_unified_registry
    from src.back.models.exceptions import ModelNotFoundError

    try:
        reg = get_unified_registry()
        record = reg.get_llm(repo_id)
        if not record:
            raise ModelNotFoundError(f"Model {repo_id} not found")
        if filename not in record.get("files", {}):
            raise ModelNotFoundError(f"File {filename} not found in {repo_id}")
        path = Path(record["files"][filename]["local_path"])
        if path.exists():
            path.unlink()
        del record["files"][filename]
        reg._save()
        return JSONResponse(
            content={"success": True, "repo_id": repo_id, "filename": filename}
        )
    except ModelNotFoundError as e:
        return JSONResponse(status_code=404, content={"error": str(e)})
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


# ============= Embedding Models =============


@router.get("/embedding/installed")
async def list_installed_embedding_models() -> JSONResponse:
    """List installed embedding models."""
    from src.api.dependencies import get_unified_registry

    try:
        reg = get_unified_registry()
        from src.shared import EMBEDDINGS_DIR

        reg.sync_embeddings_folder(EMBEDDINGS_DIR)
        embeddings = reg.list_embeddings()
        return JSONResponse(content={"models": embeddings})
    except Exception as e:
        logger.error(f"Failed to list installed embedding models: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/embedding/progress/{repo_id}")
async def get_embedding_progress(repo_id: str) -> JSONResponse:
    """Get embedding download progress."""
    progress = _download_progress.get(
        f"emb_{repo_id}", {"progress": 0, "status": "idle"}
    )
    return JSONResponse(content=progress)


@router.post("/embedding/download")
async def download_embedding_model(
    repo_id: str,
    filename: str | None = None,
) -> JSONResponse:
    """Download an embedding model from HuggingFace."""
    import asyncio

    from src.api.dependencies import get_embedding_manager

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

    from src.api.dependencies import get_unified_registry

    try:
        reg = get_unified_registry()
        record = reg.get_embedding(repo_id)
        if not record:
            return JSONResponse(
                status_code=404, content={"error": f"Model {repo_id} not found"}
            )
        path = Path(record.get("local_path", ""))
        if path.exists():
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        reg.remove_embedding(repo_id)
        return JSONResponse(content={"success": True, "repo_id": repo_id})
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
