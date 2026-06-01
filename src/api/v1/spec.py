"""Sigma Specification API v1 — scan and embed spec files."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from src.back.database import DatabaseService
from src.back.rag.ingestion import IngestionPipelineBuilder
from src.shared.config import get_config
from src.shared.utils import iso_now

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/spec", tags=["v1-spec"])


class SpecResponse(BaseModel):
    success: bool
    message: str | None = None
    data: Any = None
    error: str | None = None


_SELECTED_DIRS_KEY = "sigma_spec_selected_dirs"
_SUPPORTED_EXTS = frozenset({".md", ".yaml", ".yml", ".json", ".txt"})


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
    if not selected:
        return []

    files: list[Path] = []
    for entry in spec_dir.iterdir():
        if entry.is_dir() and entry.name in selected:
            for f in entry.rglob("*"):
                if f.is_file() and f.suffix.lower() in _SUPPORTED_EXTS:
                    files.append(f)

    return sorted(set(files))


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
    entries: list[dict[str, Any]] = []

    for f in _walk_selected(spec_dir):
        rel = f.relative_to(spec_dir).as_posix()
        url = f"spec://sigma-specification/{rel}"
        url_hash = hashlib.sha256(url.encode()).hexdigest()

        content_hash = hashlib.sha256(f.read_bytes()).hexdigest()
        file_size = f.stat().st_size

        ct = "markdown" if f.suffix.lower() == ".md" else f.suffix.lower().lstrip(".")

        entries.append(
            {
                "url_hash": url_hash,
                "org": "sigma_spec",
                "repo": "sigma-specification",
                "content_type": ct,
                "file_name": rel,
                "content_sha256": content_hash,
                "file_size": file_size,
                "original_url": url,
                "normalized_url": url,
                "rule_id": "00000000-0000-0000-0000-000000000000",
                "title": f.stem,
                "timestamp": iso_now(),
                "last_seen": iso_now(),
                "embed_status": "discovery",
            }
        )

    if entries:
        try:
            db.batch_upsert_doc_registry(entries)
        except Exception as e:
            logger.error(f"Failed to batch upsert spec entries: {e}")
            return SpecResponse(success=False, error=str(e))

    return SpecResponse(
        success=True,
        message=f"Scanned {len(entries)} specification files.",
        data={"count": len(entries)},
    )


@router.post("/embed", response_model=SpecResponse)
async def embed_spec_files() -> SpecResponse:
    """Embed all discovered sigma-spec files into Qdrant."""
    db = DatabaseService.get_instance()
    pending = db.get_pending_doc_registry(org="sigma_spec", repo="sigma-specification")
    if not pending:
        return SpecResponse(success=False, error="No pending spec files to embed. Run scan first.")

    cfg = get_config()
    spec_dir = Path(cfg.paths_sigma_spec_dir).resolve()

    from src.back.qdrant import QdrantVectorService

    qdrant = QdrantVectorService(collection_name="sigma_spec")
    await qdrant.create_collection(enable_hybrid=True)

    builder = IngestionPipelineBuilder(collection_name="sigma_spec")
    processed = 0
    errors: list[str] = []

    for entry in pending:
        file_path = spec_dir / entry.get("file_name", "")
        if not file_path.exists():
            errors.append(f"File not found: {file_path}")
            continue
        try:
            docs = builder.run_files([str(file_path)])
            if docs:
                db.update_doc_registry_embed_status(entry["url_hash"], "embedded")
                processed += 1
            else:
                errors.append(f"No docs produced for {file_path.name}")
        except Exception as e:
            logger.error(f"Failed to embed {file_path}: {e}")
            errors.append(f"{file_path.name}: {e}")

    msg = f"Embedded {processed} spec files"
    if errors:
        msg += f", {len(errors)} errors (first: {errors[0]})"

    db.persist()
    return SpecResponse(
        success=True,
        message=msg,
        data={"count": processed, "errors": errors[:5]},
    )
