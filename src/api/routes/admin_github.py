"""GitHub repository admin API routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from src.api.dependencies import get_github_repo_manager
from src.git.repo_manager import RepositoryManager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/github", tags=["admin-github"])


@router.get("/")
async def github_admin_get(
    action: str = Query(..., description="Action: list, info"),
    org: str | None = Query(None, description="GitHub organization"),
    name: str | None = Query(None, description="Repository name"),
    manager: RepositoryManager = Depends(get_github_repo_manager),
) -> JSONResponse:
    """Unified GitHub admin GET endpoint."""
    match action:
        case "list":
            repos = manager.list_with_metadata()
            return JSONResponse(content={"repos": repos})

        case "info":
            if not org or not name:
                return JSONResponse(
                    status_code=400,
                    content={"error": "org and name required for action=info"},
                )
            repo_path = manager.get_repo_path(org, name)
            if not repo_path:
                return JSONResponse(
                    status_code=404,
                    content={"error": f"Repository '{org}/{name}' not found"},
                )
            metadata = manager.get_metadata(org, name)
            return JSONResponse(
                content={
                    "org": org,
                    "name": name,
                    "path": str(repo_path),
                    "metadata": metadata,
                }
            )

        case _:
            return JSONResponse(
                status_code=400,
                content={"error": f"Unknown action: {action}"},
            )


@router.post("/")
async def github_admin_post(
    action: str = Query(..., description="Action: clone, update, delete"),
    org: str | None = Query(None, description="GitHub organization"),
    name: str | None = Query(None, description="Repository name"),
    branch: str | None = Query(None, description="Branch to use"),
    extensions_to_index: list[str] | None = Query(
        None, description="File extensions to index"
    ),
    manager: RepositoryManager = Depends(get_github_repo_manager),
) -> JSONResponse:
    """Unified GitHub admin POST endpoint."""
    match action:
        case "clone":
            if not org or not name or not branch:
                return JSONResponse(
                    status_code=400,
                    content={"error": "org, name and branch required for action=clone"},
                )

            url = f"https://github.com/{org}/{name}.git"
            result = manager.clone(url=url, org=org, name=name)
            if not result.get("success"):
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": result.get("error")},
                )

            metadata = {
                "org": org,
                "name": name,
                "branch": branch,
                "extensions_to_index": extensions_to_index or ["*.yml", "*.yaml"],
            }
            manager.save_metadata(org, name, metadata)

            return JSONResponse(
                content={
                    "success": True,
                    "message": f"Repository '{org}/{name}' cloned successfully",
                    "repo": {
                        "org": org,
                        "name": name,
                        "path": result.get("path"),
                        "metadata": metadata,
                    },
                }
            )

        case "update":
            if not org or not name:
                return JSONResponse(
                    status_code=400,
                    content={"error": "org and name required for action=update"},
                )

            metadata = manager.get_metadata(org, name)
            branch_to_pull = branch or (metadata.get("branch") if metadata else None) or "main"

            result = manager.update(org=org, name=name, branch=branch_to_pull)
            if not result.get("success"):
                return JSONResponse(
                    status_code=400,
                    content={"success": False, "error": result.get("error")},
                )

            return JSONResponse(
                content={
                    "success": True,
                    "message": f"Repository '{org}/{name}' updated successfully",
                    "repo": {
                        "org": org,
                        "name": name,
                        "path": result.get("path"),
                        "branch": result.get("branch"),
                    },
                }
            )

        case "update-metadata":
            if not org or not name:
                return JSONResponse(
                    status_code=400,
                    content={"error": "org and name required for action=update-metadata"},
                )

            # Get existing metadata or create empty dict
            metadata = manager.get_metadata(org, name) or {}
            metadata["org"] = org
            metadata["name"] = name

            # Update branch if provided
            if branch:
                metadata["branch"] = branch

            # Update extensions if provided
            if extensions_to_index is not None:
                metadata["extensions_to_index"] = extensions_to_index

            # Save updated metadata
            manager.save_metadata(org, name, metadata)

            return JSONResponse(
                content={
                    "success": True,
                    "message": f"Metadata updated for '{org}/{name}'",
                    "metadata": metadata,
                }
            )

        case "delete":
            if not org or not name:
                return JSONResponse(
                    status_code=400,
                    content={"error": "org and name required for action=delete"},
                )

            result = manager.delete(org, name)
            success = result.get("success", False)
            return JSONResponse(
                status_code=200 if success else 400,
                content={
                    "success": success,
                    "message": f"Repository '{org}/{name}' deleted" if success else None,
                    "error": result.get("error") if not success else None,
                }
            )

        case _:
            return JSONResponse(
                status_code=400,
                content={"error": f"Unknown action: {action}"},
            )
