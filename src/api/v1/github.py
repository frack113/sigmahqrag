"""GitHub Repository Management API v1."""

from pathlib import Path
import re
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from threading import Lock

import logging

from src.back.github.git import (
    _get_repo_path,
    _is_valid_repo,
    clone_repo,
    delete_repo,
    get_last_commit_date,
    get_metadata,
    get_selected_dirs,
    is_repo_outdated,
    list_directory_tree,
    list_repos,
    save_metadata,
    save_selected_dirs,
    update_repo,
)

from src.shared.config import get_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/github", tags=["v1-github"])
_sync_lock = Lock()

# Valid org/name pattern: alphanumeric, hyphens, underscores, dots (no path separators)
_VALID_ORG_NAME_RE = re.compile(r"^[\w.-]+$")


def _validate_org_name(org: str, name: str) -> None:
    """Validate org/name to prevent path traversal. Raises HTTPException if invalid."""
    if not _VALID_ORG_NAME_RE.match(org) or not _VALID_ORG_NAME_RE.match(name):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid org/name: '{org}/{name}' contains path traversal characters",
        )


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
    repo_status: str | None = None
    last_synced: datetime | str | None = None
    url: str | None = None
    branch: str | None = None
    last_commit: str | None = None
    sync_class: str = Field(
        default="btn-success", description="btn-success|btn-warning|btn-unknown"
    )


def _extract_org_name(url: str) -> tuple[str, str]:
    """Extract org and name from URL."""
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.split("/")
    if len(parts) < 2:
        raise ValueError("Invalid URL format")
    return parts[-2].lower(), parts[-1].lower()


@router.get("/repos", response_model=list[RepositoryStatus])
async def list_repos_handler() -> list[RepositoryStatus]:
    """List all repositories."""
    repos = list_repos()
    result = []
    for repo in repos:
        metadata = get_metadata(repo["org"], repo["name"]) or {}
        stored_status = metadata.get("status", "synced")

        if stored_status == "cloning" or stored_status == "syncing":
            sync_class = "btn-warning"
        elif stored_status == "error":
            sync_class = "btn-unknown"
        else:
            is_outdated = is_repo_outdated(repo["org"], repo["name"])
            sync_class = "btn-danger" if is_outdated else "btn-success"

        last_commit = get_last_commit_date(repo["org"], repo["name"])
        result.append(
            RepositoryStatus(
                org=repo["org"],
                name=repo["name"],
                repo_status=metadata.get("status", "synced"),
                last_synced=metadata.get("last_synced"),
                url=metadata.get("url"),
                branch=metadata.get("branch"),
                last_commit=last_commit,
                sync_class=sync_class,
            )
        )
    return result


@router.post("/repos", response_model=RepositoryResponse)
async def add_repo(
    request: RepositoryAddRequest,
    background_tasks=None,
):
    """Add a new repository."""
    try:
        org, name = _extract_org_name(request.url)
    except ValueError:
        return RepositoryResponse(success=False, error="Invalid URL format")

    existing = list_repos()
    if any(r["org"] == org and r["name"] == name for r in existing):
        return RepositoryResponse(success=False, error=f"Repository '{org}/{name}' already exists")

    def clone_with_status() -> None:
        with _sync_lock:
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
                        "remote_head": result.get("remote_head"),
                    },
                )
                save_selected_dirs(org, name, [])
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

    if background_tasks is not None:
        background_tasks.add_task(clone_with_status)

    return RepositoryResponse(
        success=True,
        message=f"Cloning repository '{org}/{name}' in background",
        data={"org": org, "name": name, "status": "cloning"},
    )


@router.get("/repos/{org}/{name}", response_model=RepositoryStatus)
async def get_repo(org: str, name: str) -> RepositoryStatus:
    """Get repository details."""
    _validate_org_name(org, name)
    repos = list_repos()
    if not any(r["org"] == org and r["name"] == name for r in repos):
        raise HTTPException(status_code=404, detail=f"Repository '{org}/{name}' not found")

    metadata = get_metadata(org, name) or {}
    last_commit = get_last_commit_date(org, name)
    return RepositoryStatus(
        org=org,
        name=name,
        repo_status=metadata.get("status", "synced"),
        last_synced=metadata.get("last_synced"),
        url=metadata.get("url"),
        branch=metadata.get("branch"),
        last_commit=last_commit,
    )


@router.post("/repos/{org}/{name}/sync", response_model=RepositoryResponse)
async def sync_repo(
    org: str,
    name: str,
    branch: str | None = None,
    background_tasks=None,
):
    """Sync a repository."""
    _validate_org_name(org, name)
    metadata = get_metadata(org, name)
    if branch is None:
        branch = (metadata or {}).get("branch", "main")

    if ".." in branch or branch.startswith("/") or branch.endswith("/"):
        return RepositoryResponse(success=False, error="Invalid branch name")
    if len(branch) > 255:
        return RepositoryResponse(success=False, error="Branch name too long")

    repos = list_repos()
    if not any(r["org"] == org and r["name"] == name for r in repos):
        return RepositoryResponse(success=False, error=f"Repository '{org}/{name}' not found")

    def sync_with_status() -> dict[str, Any]:
        with _sync_lock:
            result = update_repo(org=org, name=name, branch=branch)
            existing_meta = get_metadata(org, name) or {}
            if result.get("success"):
                merged = {
                    **existing_meta,
                    "org": org,
                    "name": name,
                    "branch": branch,
                    "status": "synced",
                    "last_synced": datetime.now().isoformat(),
                    "remote_head": result.get("remote_head"),
                }
                save_metadata(org, name, merged)
        return result

    if background_tasks is not None:
        background_tasks.add_task(sync_with_status)

    return RepositoryResponse(success=True, message="Sync started in background")


@router.post("/repos/sync-all", response_model=RepositoryResponse)
async def sync_all_repos(
    background_tasks=None,
):
    """Sync all registered repositories."""
    repos = list_repos()
    if not repos:
        return RepositoryResponse(success=True, message="No repositories to sync")

    def sync_all_task() -> None:
        for repo in list(repos):
            repo_data = {k: repo[k] for k in ("org", "name")}
            try:
                with _sync_lock:
                    meta = get_metadata(repo_data["org"], repo_data["name"]) or {}
                    branch = meta.get("branch", "main")
                    result = update_repo(
                        org=repo_data["org"], name=repo_data["name"], branch=branch
                    )
                    existing_meta = get_metadata(repo_data["org"], repo_data["name"]) or {}
                    merged = {
                        **existing_meta,
                        "org": repo_data["org"],
                        "name": repo_data["name"],
                        "branch": branch,
                        "status": "synced",
                        "last_synced": datetime.now().isoformat(),
                        "remote_head": result.get("remote_head"),
                    }
                    save_metadata(repo_data["org"], repo_data["name"], merged)
            except Exception as e:
                logger.error(f"Failed to sync {repo_data['org']}/{repo_data['name']}: {e}")

    if background_tasks is not None:
        background_tasks.add_task(sync_all_task)

    return RepositoryResponse(success=True, message="Sync started for all repositories")


@router.delete("/repos/{org}/{name}", response_model=RepositoryResponse)
async def delete_repo_handler(
    org: str,
    name: str,
) -> RepositoryResponse:
    """Delete a repository."""
    try:
        _validate_org_name(org, name)
    except HTTPException as e:
        return RepositoryResponse(success=False, error=e.detail)
    result = delete_repo(org, name)
    if result.get("success"):
        return RepositoryResponse(success=True, message=f"Repository '{org}/{name}' deleted")
    return RepositoryResponse(success=False, error=result.get("error", "Delete failed"))


@router.get("/repos/{org}/{name}/status", response_model=RepositoryStatus)
async def get_repo_status(org: str, name: str) -> RepositoryStatus:
    """Get repository status."""
    _validate_org_name(org, name)
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


class DirectoryTreeResponse(BaseModel):
    """Response for directory tree listing."""

    success: bool
    tree: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class SelectDirsRequest(BaseModel):
    """Request to save selected directories."""

    selected: list[str] = Field(default_factory=list, description="List of folder paths")


class SelectDirsResponse(BaseModel):
    """Response for saving selected directories."""

    success: bool
    message: str | None = None
    error: str | None = None


@router.get("/repos/{org}/{name}/tree", response_model=DirectoryTreeResponse)
async def get_repo_tree(
    org: str,
    name: str,
    max_depth: int = 5,
) -> DirectoryTreeResponse:
    """Get directory tree for a repository."""
    try:
        _validate_org_name(org, name)
    except HTTPException as e:
        return DirectoryTreeResponse(success=False, error=e.detail)
    try:
        # Check repo exists on filesystem directly (avoids fetching all repos)
        repos_dir = Path(get_config().paths_github_dir)
        repo_path = _get_repo_path(repos_dir, org, name)
        if not repo_path.exists() or not _is_valid_repo(repo_path):
            # Check DB — registered but not cloned locally?
            try:
                metadata = get_metadata(org, name)
                if metadata:
                    return DirectoryTreeResponse(
                        success=False,
                        error=f"Repository '{org}/{name}' not cloned yet",
                    )
            except Exception as db_err:
                logger.debug(f"Could not check DB for {org}/{name}: {db_err}")
            return DirectoryTreeResponse(
                success=False,
                error=f"Repository '{org}/{name}' not found or not cloned yet",
            )

        tree = list_directory_tree(org, name, max_depth=max_depth)
        selected: list[str] = []
        try:
            selected = get_selected_dirs(org, name) or []
        except Exception as db_err:
            logger.debug(f"Could not load selected dirs for {org}/{name}: {db_err}")

        for node in tree:
            _mark_selected(node, selected)

        return DirectoryTreeResponse(
            success=True,
            tree=tree,
        )
    except PermissionError as e:
        logger.error(f"Permission denied accessing repo dir for {org}/{name}: {e}")
        return DirectoryTreeResponse(
            success=False,
            error="Permission denied accessing repository directory",
        )
    except Exception as e:
        logger.error(f"Failed to get tree for {org}/{name}: {type(e).__name__}: {e}")
        import traceback

        logger.error(traceback.format_exc())
        return DirectoryTreeResponse(
            success=False,
            error=f"Error loading directory structure: {type(e).__name__}",
        )


def _mark_selected(node: dict[str, Any], selected: list[str]) -> None:
    """Mark nodes as selected based on their path."""
    if node.get("path") in selected:
        node["selected"] = True
    if "children" in node:
        for child in node["children"]:
            _mark_selected(child, selected)


@router.post("/repos/{org}/{name}/select-dirs", response_model=SelectDirsResponse)
async def select_dirs(
    org: str,
    name: str,
    request: SelectDirsRequest,
) -> SelectDirsResponse:
    """Save selected directories for a repository."""
    try:
        _validate_org_name(org, name)
    except HTTPException as e:
        return SelectDirsResponse(success=False, error=e.detail)
    try:
        repo_path = _get_repo_path(Path(get_config().paths_github_dir), org, name)
        if not repo_path.exists() or not _is_valid_repo(repo_path):
            return SelectDirsResponse(success=False, error=f"Repository '{org}/{name}' not found")
    except Exception as e:
        return SelectDirsResponse(success=False, error=str(e))
    result = save_selected_dirs(org, name, request.selected)
    if result.get("success"):
        return SelectDirsResponse(
            success=True,
            message=f"Saved {len(request.selected)} selected directories for {org}/{name}",
        )
    return SelectDirsResponse(
        success=False,
        error=result.get("error", "Failed to save selections"),
    )
