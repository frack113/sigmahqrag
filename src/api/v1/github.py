"""GitHub Repository Management API v1."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field

from src.api.dependencies import get_github_repo_manager
from src.back.backend.github.repo import RepositoryManager

router = APIRouter(prefix="/api/v1/github", tags=["v1-github"])


class RepositoryAddRequest(BaseModel):
    """Request to add a new repository."""

    url: str = Field(..., description="Git repository URL")
    branch: str = Field(default="main", description="Branch to clone")


class RepositoryResponse(BaseModel):
    """Response for repository operations."""

    success: bool
    message: str | None = None
    data: dict[str, Any] | None = None
    error: str | None = None


class RepositoryStatus(BaseModel):
    """Repository status information."""

    org: str
    name: str
    repo_status: str = Field(..., description="synced|outdated|error|cloning|syncing")
    last_synced: datetime | None = None
    url: str | None = None
    branch: str | None = None


def _run_clone_task(manager: RepositoryManager, url: str, org: str, name: str) -> None:
    """Background task to clone repository."""
    manager.clone(url=url, org=org, name=name)


def _run_sync_task(
    manager: RepositoryManager, org: str, name: str, branch: str
) -> dict[str, Any]:
    """Background task to sync repository."""
    return manager.update(org=org, name=name, branch=branch)


@router.get("/repos", response_model=list[RepositoryStatus])
async def list_repos(
    manager: RepositoryManager = Depends(get_github_repo_manager),
) -> list[RepositoryStatus]:
    """List all repositories."""
    repos = manager.list_with_metadata()
    result = []
    for repo in repos:
        metadata = repo.get("metadata", {})
        status_val = "synced"
        if metadata.get("status"):
            status_val = metadata["status"]
        result.append(
            RepositoryStatus(
                org=repo["org"],
                name=repo["name"],
                repo_status=status_val,
                last_synced=metadata.get("last_synced"),
                url=metadata.get("url"),
                branch=metadata.get("branch"),
            )
        )
    return result


@router.post("/repos", response_model=RepositoryResponse)
async def add_repo(
    request: RepositoryAddRequest,
    background_tasks: BackgroundTasks = None,
    manager: RepositoryManager = Depends(get_github_repo_manager),
) -> RepositoryResponse:
    """Add a new repository."""
    url = request.url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.split("/")
    if len(parts) < 2:
        return RepositoryResponse(
            success=False,
            error="Invalid URL format",
        )
    name = parts[-1]
    org = parts[-2]

    existing = manager.get_repo_path(org, name)
    if existing:
        return RepositoryResponse(
            success=False,
            error=f"Repository '{org}/{name}' already exists",
        )

    def clone_with_status() -> None:
        result = manager.clone(url=request.url, org=org, name=name)
        if result.get("success"):
            manager.save_metadata(
                org,
                name,
                {
                    "org": org,
                    "name": name,
                    "url": request.url,
                    "branch": request.branch,
                    "status": "synced",
                    "last_synced": datetime.now().isoformat(),
                    "created_at": datetime.now().isoformat(),
                },
            )
        else:
            manager.save_metadata(
                org,
                name,
                {
                    "org": org,
                    "name": name,
                    "url": request.url,
                    "branch": request.branch,
                    "status": "error",
                    "error": result.get("error"),
                },
            )

    background_tasks.add_task(clone_with_status)

    return RepositoryResponse(
        success=True,
        message=f"Cloning repository '{org}/{name}' in background",
        data={"org": org, "name": name, "status": "cloning"},
    )


@router.get("/repos/{org}/{name}", response_model=RepositoryStatus)
async def get_repo(
    org: str,
    name: str,
    manager: RepositoryManager = Depends(get_github_repo_manager),
) -> RepositoryStatus:
    """Get repository details."""
    repo_path = manager.get_repo_path(org, name)
    if not repo_path:
        raise HTTPException(
            status_code=404, detail=f"Repository '{org}/{name}' not found"
        )

    metadata = manager.get_metadata(org, name) or {}
    return RepositoryStatus(
        org=org,
        name=name,
        repo_status=metadata.get("status", "synced"),
        last_synced=metadata.get("last_synced"),
        url=metadata.get("url"),
        branch=metadata.get("branch"),
    )


@router.post("/repos/{org}/{name}/sync", response_model=RepositoryResponse)
async def sync_repo(
    org: str,
    name: str,
    branch: str = "main",
    background_tasks: BackgroundTasks = None,
    manager: RepositoryManager = Depends(get_github_repo_manager),
) -> RepositoryResponse:
    """Sync a repository."""
    if ".." in branch or branch.startswith("/") or branch.endswith("/"):
        return RepositoryResponse(
            success=False,
            error="Invalid branch name",
        )
    if len(branch) > 255:
        return RepositoryResponse(
            success=False,
            error="Branch name too long",
        )
    repo_path = manager.get_repo_path(org, name)
    if not repo_path:
        return RepositoryResponse(
            success=False,
            error=f"Repository '{org}/{name}' not found",
        )

    def sync_with_status() -> dict[str, Any]:
        result = manager.update(org=org, name=name, branch=branch)
        if result.get("success"):
            manager.save_metadata(
                org,
                name,
                {
                    "status": "synced",
                    "last_synced": datetime.now().isoformat(),
                },
            )
        return result

    background_tasks.add_task(sync_with_status)

    return RepositoryResponse(
        success=True,
        message=f"Syncing repository '{org}/{name}' in background",
        data={"org": org, "name": name, "status": "syncing"},
    )


@router.delete("/repos/{org}/{name}", response_model=RepositoryResponse)
async def delete_repo(
    org: str,
    name: str,
    manager: RepositoryManager = Depends(get_github_repo_manager),
) -> RepositoryResponse:
    """Delete a repository."""
    result = manager.delete(org, name)
    if result.get("success"):
        return RepositoryResponse(
            success=True,
            message=f"Repository '{org}/{name}' deleted",
        )
    return RepositoryResponse(
        success=False,
        error=result.get("error", "Delete failed"),
    )


@router.get("/repos/{org}/{name}/status", response_model=RepositoryStatus)
async def get_repo_status(
    org: str,
    name: str,
    manager: RepositoryManager = Depends(get_github_repo_manager),
) -> RepositoryStatus:
    """Get repository status."""
    repo_path = manager.get_repo_path(org, name)
    if not repo_path:
        return RepositoryStatus(
            org=org,
            name=name,
            repo_status="error",
        )

    metadata = manager.get_metadata(org, name) or {}
    return RepositoryStatus(
        org=org,
        name=name,
        repo_status=metadata.get("status", "synced"),
        last_synced=metadata.get("last_synced"),
        url=metadata.get("url"),
        branch=metadata.get("branch"),
    )


def get_github_repo_manager() -> RepositoryManager:
    """Dependency to get repository manager."""
    from src.api.dependencies import get_github_repo_manager as _get_manager

    return _get_manager()

