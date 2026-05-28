"""Admin model management endpoints."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.api.dependencies import get_database_service, get_unified_registry
from src.back.models import ModelNotFoundError
from src.shared import LLM_DIR, EMBEDDINGS_DIR

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
    try:
        reg = get_unified_registry()
        repo_id = request.get("repo_id")
        filename = request.get("filename")

        if not repo_id or not filename:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": "repo_id and filename required"},
            )

        if (
            ".." in repo_id
            or repo_id.count("/") != 1
            or repo_id.startswith("/")
            or repo_id.endswith("/")
        ):
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": "Invalid repo_id"},
            )

        db = get_database_service()
        record = reg.get_llm(repo_id, db)
        if not record:
            raise ModelNotFoundError(f"Model {repo_id} not found")
        if filename not in record.get("files", {}):
            raise ModelNotFoundError(f"File {filename} not found in {repo_id}")
        path = Path(record["files"][filename]["local_path"]).resolve()
        try:
            path.relative_to(Path(LLM_DIR).resolve())
        except ValueError:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": "Invalid file path"},
            )
        if path.exists():
            path.unlink()
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

        return JSONResponse(
            content={"status": "success", "message": f"Deleted {repo_id}/{filename}"}
        )
    except ModelNotFoundError as e:
        return JSONResponse(status_code=404, content={"status": "error", "error": str(e)})
    except Exception as e:
        logger.error(f"Failed to delete model: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "An internal error occurred"},
        )


@router.post("/models/delete-embedding")
async def delete_embedding_model(request: dict) -> JSONResponse:
    """POST /api/v1/admin/models/delete-embedding - Delete an embedding model."""
    import shutil

    try:
        reg = get_unified_registry()
        repo_id = request.get("repo_id")

        if not repo_id:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": "repo_id required"},
            )

        if ".." in repo_id:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "error": "Invalid repo_id"},
            )

        db = get_database_service()
        record = reg.get_embedding(repo_id, db)
        if not record:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "error": f"Model {repo_id} not found"},
            )

        local_path = record.get("local_path", "")
        if local_path:
            path = Path(local_path).resolve()
            try:
                path.relative_to(Path(EMBEDDINGS_DIR).resolve())
            except ValueError:
                return JSONResponse(
                    status_code=400,
                    content={"status": "error", "error": "Invalid file path"},
                )
            if path.exists():
                if path.is_dir():
                    shutil.rmtree(path)
                else:
                    path.unlink()

        reg.remove_embedding(repo_id, db)
        return JSONResponse(
            content={"status": "success", "message": f"Deleted embedding {repo_id}"}
        )
    except Exception as e:
        logger.error(f"Failed to delete embedding model: {e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": "An internal error occurred"},
        )
