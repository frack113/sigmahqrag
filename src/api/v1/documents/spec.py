"""Sigma Specification Repository Management API v1."""

import logging
import re
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from src.config.settings import get_config
from src.infrastructure.database import DatabaseService
from src.infrastructure.github.git import (
    clone_repo,
    delete_repo,
    get_last_commit_date,
    get_metadata,
    list_directory_tree,
    list_repos,
    save_metadata,
    save_selected_dirs,
    update_repo,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/spec", tags=["v1-spec"])

_sync_lock = Lock()

# Valid org/name pattern: alphanumeric, hyphens, underscores, dots (no path separators)
_VALID_ORG_NAME_RE = re.compile(r"^(?!\.\.?$)[\w.-]+$")


def _spec_repos_dir() -> Path:
    return Path(get_config().paths_spec_repos_dir).resolve()


def _validate_org_name(org: str, name: str) -> None:
    """Validate org/name to prevent path traversal. Raises HTTPException if invalid."""
    if not _VALID_ORG_NAME_RE.match(org) or not _VALID_ORG_NAME_RE.match(name):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid org/name: '{org}/{name}' contains path traversal characters",
        )


class SpecResponse(BaseModel):
    success: bool
    message: str | None = None
    data: Any = None
    error: str | None = None


class RepositoryAddRequest(BaseModel):
    """Request to add a new specification repository."""

    url: str = Field(..., description="Git repository URL")
    branch: str = Field(default="main", description="Branch to clone")


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


def _extract_org_name(url: str) -> tuple[str, str]:
    """Extract org and name from URL."""
    url = url.rstrip("/")
    if url.endswith(".git"):
        url = url[:-4]
    parts = url.split("/")
    if len(parts) < 2:
        raise ValueError("Invalid URL format")
    return parts[-2].lower(), parts[-1].lower()


def _sync_single_repo(org: str, name: str, branch: str | None = None) -> dict[str, Any]:
    """Sync a single spec repository and save metadata. Runs under _sync_lock."""
    with _sync_lock:
        meta = get_metadata(org, name) or {}
        resolved_branch = branch or meta.get("branch", "main")
        result = update_repo(
            org=org, name=name, branch=resolved_branch, repos_dir=_spec_repos_dir()
        )
        if result.get("success"):
            merged = {
                **meta,
                "org": org,
                "name": name,
                "branch": resolved_branch,
                "status": "synced",
                "last_synced": datetime.now().isoformat(),
                "remote_head": result.get("remote_head"),
            }
            save_metadata(org, name, merged, repos_dir=_spec_repos_dir())
    return result


@router.get("/repos", response_model=list[RepositoryStatus])
async def list_repos_handler() -> list[RepositoryStatus]:
    """List all spec repositories."""
    repos = list_repos(repos_dir=_spec_repos_dir())
    result = []
    for repo in repos:
        metadata = get_metadata(repo["org"], repo["name"]) or {}
        stored_status = metadata.get("status", "synced")

        if stored_status == "cloning" or stored_status == "syncing":
            sync_class = "btn-warning"
        elif stored_status == "error":
            sync_class = "btn-unknown"
        else:
            sync_class = "btn-success"

        last_commit = get_last_commit_date(repo["org"], repo["name"], repos_dir=_spec_repos_dir())
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


@router.post("/repos", response_model=SpecResponse)
async def add_repo(
    request: RepositoryAddRequest,
    background_tasks: BackgroundTasks,
):
    """Add a new specification repository."""
    try:
        org, name = _extract_org_name(request.url)
    except ValueError:
        return SpecResponse(success=False, error="Invalid URL format")

    existing = list_repos(repos_dir=_spec_repos_dir())
    if any(r["org"] == org and r["name"] == name for r in existing):
        return SpecResponse(success=False, error=f"Repository '{org}/{name}' already exists")

    def clone_with_status() -> None:
        with _sync_lock:
            result = clone_repo(url=request.url, repos_dir=_spec_repos_dir(), branch=request.branch)
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
                    repos_dir=_spec_repos_dir(),
                )
                save_selected_dirs(org, name, [], repos_dir=_spec_repos_dir())
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
                    repos_dir=_spec_repos_dir(),
                )

    background_tasks.add_task(clone_with_status)

    return SpecResponse(
        success=True,
        message=f"Cloning repository '{org}/{name}' in background",
        data={"org": org, "name": name, "status": "cloning"},
    )


@router.post("/repos/sync-all", response_model=SpecResponse)
async def sync_all_repos(
    background_tasks: BackgroundTasks,
):
    """Sync all registered specification repositories."""
    repos = list_repos(repos_dir=_spec_repos_dir())
    if not repos:
        return SpecResponse(success=True, message="No repositories to sync")

    def sync_all_task() -> None:
        for repo_data in list(repos):
            try:
                _sync_single_repo(repo_data["org"], repo_data["name"])
            except Exception as e:
                logger.error(f"Failed to sync {repo_data['org']}/{repo_data['name']}: {e}")

    background_tasks.add_task(sync_all_task)

    return SpecResponse(success=True, message="Sync started for all repositories")


@router.delete("/repos/{org}/{name}", response_model=SpecResponse)
async def delete_repo_handler(
    org: str,
    name: str,
) -> SpecResponse:
    """Delete a specification repository."""
    try:
        _validate_org_name(org, name)
    except HTTPException as e:
        return SpecResponse(success=False, error=e.detail)
    result = delete_repo(org, name, repos_dir=_spec_repos_dir())
    if result.get("success"):
        try:
            db = DatabaseService.get_instance()
            db.delete_sigma_spec_by_org_repo(org, name)
            logger.info("Cleaned up sigma_spec entries for %s/%s", org, name)
        except Exception as e:
            logger.error("Failed to clean up sigma_spec for %s/%s: %s", org, name, e)
        return SpecResponse(
            success=True,
            message=f"Repository '{org}/{name}' deleted and sigma_spec entries cleaned up",
        )
    return SpecResponse(success=False, error=result.get("error", "Delete failed"))


@router.get("/repos/{org}/{name}/sync", response_model=SpecResponse)
async def sync_repo(
    org: str,
    name: str,
    background_tasks: BackgroundTasks,
    branch: str | None = None,
):
    """Sync a specification repository."""
    _validate_org_name(org, name)
    metadata = get_metadata(org, name)
    if branch is None:
        branch = (metadata or {}).get("branch", "main")

    if branch and (".." in branch or branch.startswith("/") or branch.endswith("/")):
        return SpecResponse(success=False, error="Invalid branch name")
    if len(branch) > 255:
        return SpecResponse(success=False, error="Branch name too long")

    repos = list_repos(repos_dir=_spec_repos_dir())
    if not any(r["org"] == org and r["name"] == name for r in repos):
        return SpecResponse(success=False, error=f"Repository '{org}/{name}' not found")

    background_tasks.add_task(_sync_single_repo, org, name, branch)

    return SpecResponse(success=True, message="Sync started in background")


@router.get("/repos/{org}/{name}/tree", response_model=DirectoryTreeResponse)
async def get_repo_tree(
    org: str,
    name: str,
    max_depth: int = 5,
) -> DirectoryTreeResponse:
    """Get directory tree for a specification repository."""
    try:
        _validate_org_name(org, name)
    except HTTPException as e:
        return DirectoryTreeResponse(success=False, error=e.detail)
    try:
        repo_path = _get_repo_path(_spec_repos_dir(), org, name)
        if not repo_path.exists():
            metadata = get_metadata(org, name, repos_dir=_spec_repos_dir())
            if metadata:
                return DirectoryTreeResponse(
                    success=False,
                    error=f"Repository '{org}/{name}' not cloned yet",
                )
            return DirectoryTreeResponse(
                success=False,
                error=f"Repository '{org}/{name}' not found or not cloned yet",
            )

        tree = list_directory_tree(org, name, repos_dir=_spec_repos_dir(), max_depth=max_depth)

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
        return DirectoryTreeResponse(
            success=False,
            error=f"Error loading directory structure: {type(e).__name__}",
        )


@router.post("/repos/{org}/{name}/select-dirs", response_model=SelectDirsResponse)
async def select_dirs(
    org: str,
    name: str,
    request: SelectDirsRequest,
) -> SelectDirsResponse:
    """Save selected directories for a specification repository."""
    try:
        _validate_org_name(org, name)
    except HTTPException as e:
        return SelectDirsResponse(success=False, error=e.detail)
    try:
        repo_path = _get_repo_path(_spec_repos_dir(), org, name)
        if not repo_path.exists():
            return SelectDirsResponse(success=False, error=f"Repository '{org}/{name}' not found")
    except Exception as e:
        return SelectDirsResponse(success=False, error=str(e))
    result = save_selected_dirs(org, name, request.selected, repos_dir=_spec_repos_dir())
    if result.get("success"):
        return SelectDirsResponse(
            success=True,
            message=f"Saved {len(request.selected)} selected directories for {org}/{name}",
        )
    return SelectDirsResponse(
        success=False,
        error=result.get("error", "Failed to save selections"),
    )


def _get_repo_path(repos_dir: Path, org: str, name: str) -> Path:
    """Get the full path for a repository."""
    _validate_org_name(org, name)
    return repos_dir / org / name
