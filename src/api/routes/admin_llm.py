"""LLM API routes for HuggingFace models."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from src.api.dependencies import get_model_manager
from src.core.backend.services.download import DownloadError
from src.core.backend.services.manager import ModelManager, ModelNotFoundError
from src.core.types import HFRepo

logger = logging.getLogger(__name__)


router = APIRouter(prefix="/admin/llm", tags=["admin-llm"])


@router.get("/")
async def llm_endpoint(
    action: str = Query(..., description="Action: list, installed, info"),
    repo_id: str | None = Query(None, description="HuggingFace repo ID"),
    mm: ModelManager = Depends(get_model_manager),
) -> JSONResponse:
    """Unified LLM endpoint with action parameter."""
    try:
        match action:
            case "list":
                if not repo_id:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "repo_id required for action=list"},
                    )
                files = mm.download_service.list_gguf_files(HFRepo.from_string(repo_id))
                return JSONResponse(content={"files": files})

            case "installed":
                models = await mm.list_installed_models()
                return JSONResponse(
                    content={
                        "models": [
                            {
                                "repo_id": m.repo_id,
                                "files": [
                                    {
                                        "filename": fn,
                                        "path": str(f.local_path),
                                        "size": f.file_size,
                                        "status": f.status,
                                    }
                                    for fn, f in m.files.items()
                                ],
                                "status": m.status,
                            }
                            for m in models
                        ]
                    }
                )

            case "info":
                if not repo_id:
                    return JSONResponse(
                        status_code=400,
                        content={"error": "repo_id required for action=info"},
                    )
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
                            size = f.size
                            if size is None:
                                size = 0
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

            case _:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Unknown action: {action}"},
                )

    except DownloadError as e:
        logger.error(f"Action {action} failed: {e}")
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        logger.error(f"Unexpected error during {action}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.post("/")
async def llm_post_endpoint(
    action: str = Query(..., description="Action: download, delete"),
    repo_id: str = Query(..., description="HuggingFace repo ID"),
    filename: str | None = Query(None, description="Specific file to download"),
    expected_hash: str | None = Query(None, description="Expected file hash"),
    mm: ModelManager = Depends(get_model_manager),
) -> JSONResponse:
    """Unified LLM POST endpoint for write operations."""
    try:
        match action:
            case "download":
                record = await mm.download_model(
                    repo_id=repo_id,
                    filename=filename,
                    expected_hash=expected_hash,
                )
                return JSONResponse(
                    content={
                        "success": True,
                        "repo_id": repo_id,
                        "path": str(record.local_path),
                        "size": record.file_size,
                    }
                )

            case "delete":
                await mm.delete_model(repo_id, filename)
                return JSONResponse(
                    content={"success": True, "repo_id": repo_id, "filename": filename}
                )

            case _:
                return JSONResponse(
                    status_code=400,
                    content={"error": f"Unknown action: {action}"},
                )

    except ModelNotFoundError as e:
        logger.error(f"Action {action} failed: {e}")
        return JSONResponse(status_code=404, content={"error": str(e)})
    except DownloadError as e:
        logger.error(f"Action {action} failed: {e}")
        return JSONResponse(status_code=400, content={"error": str(e)})
    except Exception as e:
        logger.error(f"Unexpected error during {action}: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
