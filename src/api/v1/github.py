"""GitHub Repository Management API v1."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from src.back.github.git import (
    clone_repo,
    delete_repo,
    get_metadata,
    list_repos,
    save_metadata,
    update_repo,
)

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


def _extract_org_name(url: str) -> tuple[str, str]:
    """Extract org and name from URL."""
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.split("/")
    if len(parts) < 2:
        raise ValueError("Invalid URL format")
    return parts[-2], parts[-1]


@router.get("/repos", response_model=list[RepositoryStatus])
async def list_repos_handler() -> list[RepositoryStatus]:
    """List all repositories."""
    repos = list_repos()
    result = []
    for repo in repos:
        metadata = get_metadata(repo["org"], repo["name"]) or {}
        status_val = metadata.get("status", "synced")
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
) -> RepositoryResponse:
    """Add a new repository."""
    try:
        org, name = _extract_org_name(request.url)
    except ValueError:
        return RepositoryResponse(success=False, error="Invalid URL format")

    existing = list_repos()
    if any(r["org"] == org and r["name"] == name for r in existing):
        return RepositoryResponse(
            success=False, error=f"Repository '{org}/{name}' already exists"
        )

    def clone_with_status() -> None:
        result = clone_repo(url=request.url, branch=request.branch)
        if result.get("success"):
            save_metadata(
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
            save_metadata(
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
async def get_repo(org: str, name: str) -> RepositoryStatus:
    """Get repository details."""
    repos = list_repos()
    if not any(r["org"] == org and r["name"] == name for r in repos):
        raise HTTPException(
            status_code=404, detail=f"Repository '{org}/{name}' not found"
        )

    metadata = get_metadata(org, name) or {}
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
) -> RepositoryResponse:
    """Sync a repository."""
    if ".." in branch or branch.startswith("/") or branch.endswith("/"):
        return RepositoryResponse(success=False, error="Invalid branch name")
    if len(branch) > 255:
        return RepositoryResponse(success=False, error="Branch name too long")

    repos = list_repos()
    if not any(r["org"] == org and r["name"] == name for r in repos):
        return RepositoryResponse(
            success=False, error=f"Repository '{org}/{name}' not found"
        )

    def sync_with_status() -> dict[str, Any]:
        result = update_repo(org=org, name=name, branch=branch)
        if result.get("success"):
            save_metadata(
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
async def delete_repo_handler(
    org: str,
    name: str,
) -> RepositoryResponse:
    """Delete a repository."""
    result = delete_repo(org, name)
    if result.get("success"):
        return RepositoryResponse(
            success=True, message=f"Repository '{org}/{name}' deleted"
        )
    return RepositoryResponse(success=False, error=result.get("error", "Delete failed"))


@router.get("/repos/{org}/{name}/status", response_model=RepositoryStatus)
async def get_repo_status(org: str, name: str) -> RepositoryStatus:
    """Get repository status."""
    repos = list_repos()
    if not any(r["org"] == org and r["name"] == name for r in repos):
        return RepositoryStatus(org=org, name=name, repo_status="error")

    metadata = get_metadata(org, name) or {}
    return RepositoryStatus(
        org=org,
        name=name,
        repo_status=metadata.get("status", "synced"),
        last_synced=metadata.get("last_synced"),
        url=metadata.get("url"),
        branch=metadata.get("branch"),
    )
