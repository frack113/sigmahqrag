"""GitHub Repository Management API v1."""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from src.back.documents.sigma_ref_downloader import download_references
from src.back.github.git import (
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
from src.back.database.service import DatabaseService
from src.back.utils.identify_file_type import SUPPORTED_DOC_EXTENSION_MAP

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
    last_synced: datetime | None = None
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
    return parts[-2], parts[-1]


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
    background_tasks: BackgroundTasks = None,
) -> RepositoryResponse:
    """Add a new repository."""
    try:
        org, name = _extract_org_name(request.url)
    except ValueError:
        return RepositoryResponse(success=False, error="Invalid URL format")

    existing = list_repos()
    if any(r["org"] == org and r["name"] == name for r in existing):
        return RepositoryResponse(success=False, error=f"Repository '{org}/{name}' already exists")

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
        raise HTTPException(status_code=404, detail=f"Repository '{org}/{name}' not found")

    metadata = get_metadata(org, name) or {}
    return RepositoryStatus(
        org=org,
        name=name,
        repo_status=metadata.get("status", "synced"),
        last_synced=metadata.get("last_synced"),
        url=metadata.get("url"),
        branch=metadata.get("branch"),
    )


def _scan_repo_files(db: DatabaseService, base_path: Path, org: str, repo: str) -> int:
    """Scan a repo directory and register all supported files in doc_registry.

    Returns the number of files registered.
    """
    logger = __import__("logging").getLogger(__name__)
    logger.info(
        f"_scan_repo_files: base_path={base_path}, org={org}, repo={repo}, exists={base_path.exists()}"
    )
    if not base_path.exists():
        return 0

    selected_dirs = []
    repo_key = f"{org}/{repo}"
    if org and repo:
        try:
            selected_dirs = db.get_selected_dirs(repo_key)
        except Exception:
            selected_dirs = []

    files_found = 0
    for ext in SUPPORTED_DOC_EXTENSION_MAP.keys():
        # ext already includes the dot (e.g. '.md', '.markdown'), so strip it for glob
        pattern = f"**/*{ext}"
        for found_file in base_path.glob(pattern):
            rel_path = found_file.relative_to(base_path).as_posix()

            # If selected_dirs is set, filter by them
            if selected_dirs:
                if not any(rel_path.startswith(sd.lstrip("./")) for sd in selected_dirs):
                    continue

            # Compute hash and size
            try:
                file_bytes = found_file.read_bytes()
                content_hash = hashlib.sha256(file_bytes).hexdigest()
                file_size = found_file.stat().st_size
            except Exception:
                content_hash = ""
                file_size = 0

            # Determine content type
            rel_lower = rel_path.lower()
            if rel_lower.startswith("rules") or "/rules/" in rel_lower:
                content_type = "rules"
            elif rel_lower.startswith("specification") or "/specification/" in rel_lower:
                content_type = "specification"
            else:
                content_type = ext.lstrip(".")

            db.upsert_doc_registry(
                {
                    "org": org,
                    "repo": repo,
                    "content_type": content_type,
                    "file_name": rel_path,
                    "content_hash": content_hash,
                    "file_size": file_size,
                    "status": "discovered",
                }
            )
            files_found += 1

    return files_found


@router.post("/scan-all", response_model=RepositoryResponse)
async def scan_all_repos(background_tasks: BackgroundTasks = None) -> RepositoryResponse:
    """Scan all repositories and register discovered files in doc_registry."""
    db = DatabaseService.get_instance()
    try:
        repos = list_repos()
        total_files = 0

        for repo in repos:
            org = repo.get("org", "")
            name = repo.get("name", "")
            base_path = Path("data/github") / org / name
            count = _scan_repo_files(db, base_path, org, name)
            total_files += count

        # Also scan local data/documents if it exists
        local_path = Path("data/documents")
        if local_path.exists():
            count = _scan_repo_files(db, local_path, "", "")
            total_files += count

        return RepositoryResponse(
            success=True,
            message=f"Scan complete: {total_files} files registered in doc_registry",
        )
    except Exception as e:
        return RepositoryResponse(success=False, error=str(e))


@router.post("/repos/{org}/{name}/sync", response_model=RepositoryResponse)
async def sync_repo(
    org: str,
    name: str,
    branch: str | None = None,
    background_tasks: BackgroundTasks = None,
) -> RepositoryResponse:
    """Sync a repository."""
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
        result = update_repo(org=org, name=name, branch=branch)
        if result.get("success"):
            save_metadata(
                org,
                name,
                {
                    "status": "synced",
                    "last_synced": datetime.now().isoformat(),
                    "branch": branch,
                },
            )
        return result

    if background_tasks is not None:
        background_tasks.add_task(sync_with_status)

    return RepositoryResponse(success=True, message="Sync started in background")


@router.delete("/repos/{org}/{name}", response_model=RepositoryResponse)
async def delete_repo_handler(
    org: str,
    name: str,
) -> RepositoryResponse:
    """Delete a repository."""
    result = delete_repo(org, name)
    if result.get("success"):
        return RepositoryResponse(success=True, message=f"Repository '{org}/{name}' deleted")
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


class DownloadRefRequest(BaseModel):
    """Request to download Sigma rule references."""

    rules_dir: str | None = Field(default=None, description="Path to Sigma rules directory")
    output_dir: str | None = Field(
        default=None, description="Path to output directory for references"
    )


class DownloadRefResponse(BaseModel):
    """Response for download-ref operation."""

    success: bool
    message: str | None = None
    summary: dict[str, Any] | None = None
    error: str | None = None


@router.post("/download-ref", response_model=DownloadRefResponse)
async def download_ref_handler(
    background_tasks: BackgroundTasks,
    request: DownloadRefRequest | None = None,
) -> DownloadRefResponse:
    """Download Sigma rule references for all managed repositories."""
    db = DatabaseService.get_instance()
    if db.is_worker_busy("sigmaref_discovery"):
        return DownloadRefResponse(
            success=False,
            error="Worker is busy - a reference download is already in progress",
        )

    if request is None:
        request = DownloadRefRequest()

    rules_dir = request.rules_dir or "data/github/sigmahq/sigma/rules"
    output_dir = request.output_dir or "data/documents/sigmaref"

    def run_with_state():
        db.upsert_worker_state(
            worker_type="sigmaref_discovery",
            status="running",
            current_task_id="download-ref",
        )
        try:
            download_references(rules_dir, output_dir)
        finally:
            db.upsert_worker_state(
                worker_type="sigmaref_discovery",
                status="idle",
                current_task_id="",
                error="",
            )

    background_tasks.add_task(run_with_state)

    return DownloadRefResponse(
        success=True,
        message="Reference download started in background",
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
    repos = list_repos()
    repo_exists = any(r["org"] == org and r["name"] == name for r in repos)

    if not repo_exists:
        return DirectoryTreeResponse(
            success=False,
            error=f"Repository '{org}/{name}' not found or not cloned yet",
        )

    tree = list_directory_tree(org, name, max_depth=max_depth)
    selected = get_selected_dirs(org, name)

    for node in tree:
        _mark_selected(node, selected)

    return DirectoryTreeResponse(
        success=True,
        tree=tree,
    )


def _mark_selected(node: dict[str, Any], selected: list[str]) -> None:
    """Mark nodes as selected based on their path."""
    if node["path"] in selected:
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
    repos = list_repos()
    if not any(r["org"] == org and r["name"] == name for r in repos):
        return SelectDirsResponse(success=False, error=f"Repository '{org}/{name}' not found")

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
