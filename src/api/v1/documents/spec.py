"""Sigma Specification API v1 — scan and embed spec files."""

from __future__ import annotations

import asyncio
import hashlib
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from src.config.constants import SIGMA_SPEC_REF, SIGMA_SPEC_REPO
from src.config.settings import get_config
from src.infrastructure.database import DatabaseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/spec", tags=["v1-spec"])


class SpecResponse(BaseModel):
    success: bool
    message: str | None = None
    data: Any = None
    error: str | None = None


_SELECTED_DIRS_KEY = "sigma_spec_selected_dirs"
_SUPPORTED_EXTS = frozenset({".md", ".pdf", ".docx", ".doc", ".pptx", ".ppt"})


def _spec_dir() -> Path:
    return Path(get_config().paths_sigma_spec_dir).resolve()


def _get_selected() -> list[str]:
    db = DatabaseService.get_instance()
    raw = db.get_config(_SELECTED_DIRS_KEY)
    if isinstance(raw, list):
        return [str(x) for x in raw]
    return []


def _set_selected(dirs: list[str]) -> None:
    db = DatabaseService.get_instance()
    db.set_config(_SELECTED_DIRS_KEY, dirs)


def _walk_selected(spec_dir: Path) -> list[Path]:
    """Walk files only from selected directories. Returns empty if none selected."""
    selected = _get_selected()
    logger.debug("_walk_selected: selected=%s", selected)
    if not selected:
        logger.debug("_walk_selected: no selection, returning empty")
        return []

    files: list[Path] = []
    for entry in spec_dir.iterdir():
        if entry.is_dir() and entry.name in selected:
            logger.debug("_walk_selected: walking dir %s", entry.name)
            for f in entry.rglob("*"):
                if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTS:
                    files.append(f)
        else:
            logger.debug("_walk_selected: skipping dir %s (not in %s)", entry.name, selected)

    logger.debug("_walk_selected: found %d files", len(files))
    return sorted(set(files))


@router.post("/sync", response_model=SpecResponse)
async def sync_spec_repo() -> SpecResponse:
    """Clone or git pull the sigma-specification repository."""
    spec_dir = _spec_dir()

    if not spec_dir.exists():
        spec_dir.parent.mkdir(parents=True, exist_ok=True)
        proc = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            "--depth",
            "1",
            "-b",
            SIGMA_SPEC_REF,
            SIGMA_SPEC_REPO,
            str(spec_dir),
        )
        await proc.wait()
        if proc.returncode != 0:
            return SpecResponse(
                success=False, error="Failed to clone sigma-specification repository"
            )
        return SpecResponse(success=True, message="Repository cloned successfully")

    proc = await asyncio.create_subprocess_exec(
        "git",
        "-C",
        str(spec_dir),
        "pull",
        "origin",
        SIGMA_SPEC_REF,
    )
    await proc.wait()
    if proc.returncode != 0:
        return SpecResponse(success=False, error="Failed to pull sigma-specification repository")
    return SpecResponse(success=True, message="Repository synced successfully")


@router.get("/dirs", response_model=SpecResponse)
async def list_spec_dirs() -> SpecResponse:
    """List top-level subdirectories of the sigma-specification repo."""
    spec_dir = _spec_dir()
    if not spec_dir.exists():
        return SpecResponse(success=False, error=f"Spec directory not found: {spec_dir}")
    dirs = sorted(d.name for d in spec_dir.iterdir() if d.is_dir() and not d.name.startswith("."))
    return SpecResponse(success=True, data={"dirs": dirs, "count": len(dirs)})


@router.get("/selected-dirs", response_model=SpecResponse)
async def get_selected_dirs() -> SpecResponse:
    """Get currently selected directories for scanning."""
    return SpecResponse(success=True, data={"selected": _get_selected()})


class SelectedDirsRequest(BaseModel):
    selected: list[str]


@router.put("/selected-dirs", response_model=SpecResponse)
async def set_selected_dirs(req: SelectedDirsRequest) -> SpecResponse:
    """Set which directories to include when scanning."""
    spec_dir = _spec_dir()
    valid = {d.name for d in spec_dir.iterdir() if d.is_dir() and not d.name.startswith(".")}
    for d in req.selected:
        if d not in valid:
            return SpecResponse(success=False, error=f"Invalid directory: {d}")
    _set_selected(req.selected)
    return SpecResponse(success=True, message=f"Selected {len(req.selected)} directories.")


@router.get("/files", response_model=SpecResponse)
async def list_spec_files() -> SpecResponse:
    """List spec files on disk, filtered by selected directories."""
    spec_dir = _spec_dir()
    if not spec_dir.exists():
        return SpecResponse(success=False, error=f"Spec directory not found: {spec_dir}")

    files = []
    for f in _walk_selected(spec_dir):
        files.append(
            {
                "name": str(f.relative_to(spec_dir)),
                "size": f.stat().st_size,
                "type": f.suffix.lower().lstrip("."),
            }
        )

    return SpecResponse(
        success=True,
        data={"files": files, "count": len(files)},
    )


@router.post("/scan", response_model=SpecResponse)
async def scan_spec_files() -> SpecResponse:
    """Scan sigma-specification directory and register files in doc_registry."""
    spec_dir = _spec_dir()
    if not spec_dir.exists():
        return SpecResponse(success=False, error=f"Spec directory not found: {spec_dir}")

    db = DatabaseService.get_instance()

    # Mark stale pending entries as skipped so they are not picked up
    # by the indexer after the user changes directory selection.
    db.mark_spec_stale_entries_skipped()
    logger.info("Marked stale sigma_spec entries as skipped")

    entries: list[dict[str, Any]] = []

    for f in _walk_selected(spec_dir):
        rel = f.relative_to(spec_dir).as_posix()
        url = f"spec://sigma-specification/{rel}"
        url_hash = hashlib.sha256(url.encode()).hexdigest()

        content_hash = hashlib.sha256(f.read_bytes()).hexdigest()
        file_size = f.stat().st_size

        ext = f.suffix.lower()
        if ext == ".md":
            ct = "markdown"
        elif ext in (".pdf",):
            ct = "pdf"
        elif ext in (".docx", ".doc"):
            ct = "docx"
        elif ext in (".pptx", ".ppt"):
            ct = "pptx"
        else:
            ct = ext.lstrip(".")

        entries.append(
            {
                "url_hash": url_hash,
                "file_name": rel,
                "content_type": ct,
                "content_sha256": content_hash,
                "file_size": file_size,
                "original_url": url,
                "title": f.stem,
                "embed_status": "discovery",
            }
        )

    if entries:
        try:
            db.batch_upsert_sigma_spec(entries)
        except Exception as e:
            logger.error(f"Failed to batch upsert spec entries: {e}")
            return SpecResponse(success=False, error=str(e))

    return SpecResponse(
        success=True,
        message=f"Scanned {len(entries)} specification files.",
        data={"count": len(entries)},
    )
