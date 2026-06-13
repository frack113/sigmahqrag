"""System infrastructure API + data directory lifecycle management."""

from __future__ import annotations

import platform
import shutil
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.config.settings import BASE_DIR, get_config
from src.application.system.datadir import DataDirManager

router = APIRouter(prefix="/api/v1/system", tags=["system"])

# ────────────────────────────────────────────────────────────────
# Health helpers
# ────────────────────────────────────────────────────────────────

_health_checker = None
_llama_service = None
_qdrant_manager = None
_db_service = None
_reg = None


# ────────────────────────────────────────────────────────────────
# System & Qdrant status
# ────────────────────────────────────────────────────────────────


@router.get("/system/status", response_model=dict)
def get_system_status():
    """Get overall system status: OS, Python, services."""
    try:
        health_checker = None
        try:
            from src.application.system.health import HealthCheckService

            health_checker = HealthCheckService()
        except Exception:
            pass

        llama_version = "unknown"
        llama_status = "unknown"
        try:
            if health_checker:
                llama_version = health_checker.get_current_version("llama") or "unknown"
                llama_status = "installed" if llama_version != "unknown" else "missing"
        except Exception:
            pass

        system_info = {
            "hostname": platform.node() or "unknown",
            "os": platform.system(),
            "os_release": platform.release(),
            "python_version": platform.python_version(),
            "cpu": platform.processor() or "unknown",
            "base_dir": str(BASE_DIR),
            "base_dir_exists": BASE_DIR.exists(),
            "db_version": "2.0",
            "llama": {
                "version": llama_version,
                "status": llama_status,
            },
        }

        return JSONResponse(content=system_info)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/qdrant/status", response_model=dict)
def get_qdrant_status():
    """Get Qdrant connection status."""
    try:
        config = get_config()
        qdrant_status = {
            "port": config.qdrant_port,
            "host": config.qdrant_host,
            "storage_path": str(Path(config.qdrant_storage_path)),
        }

        try:
            from src.infrastructure.vectorstore.storage import get_qdrant_manager

            manager = get_qdrant_manager()
            qdrant_status["connected"] = True
            qdrant_status["collections"] = list(manager.list_collections()) if manager else []
        except Exception as e:
            qdrant_status["connected"] = False
            qdrant_status["error"] = str(e)

        return JSONResponse(content=qdrant_status)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# ────────────────────────────────────────────────────────────────
# Data directory helpers
# ────────────────────────────────────────────────────────────────


class DirItem(BaseModel):
    relative: str
    exists: bool
    has_content: bool
    is_dirty: bool
    is_healthy: bool
    needs_creation: bool


def _dir_from_info(d) -> DirItem:
    """Build a DirItem from a DataDirInfo tuple."""
    p = d.absolute
    exists = p.exists() and p.is_dir()
    if not exists:
        return DirItem(
            relative=d.relative,
            exists=False,
            has_content=False,
            is_dirty=False,
            is_healthy=False,
            needs_creation=True,
        )
    items = list(p.iterdir())
    has_content = len(items) > 0
    is_dirty = any(entry.name.startswith(".") for entry in items)
    return DirItem(
        relative=d.relative,
        exists=True,
        has_content=has_content,
        is_dirty=is_dirty,
        is_healthy=not is_dirty,
        needs_creation=False,
    )


# ────────────────────────────────────────────────────────────────
# Data directory endpoints
# ────────────────────────────────────────────────────────────────


@router.get("/data-dirs", response_model=list[DirItem])
def get_data_dirs_status():
    """Return status of all official data directories (powered by DataDirManager)."""
    mgr = DataDirManager(BASE_DIR)
    return [_dir_from_info(d) for d in mgr.official_dirs()]


@router.get("/data-dirs/{relative:path}", response_model=DirItem)
def get_data_dir_status(relative: str):
    """Return status of a single official data directory."""
    mgr = DataDirManager(BASE_DIR)
    for d in mgr.official_dirs():
        if d.relative == relative:
            return _dir_from_info(d)
    raise HTTPException(
        status_code=404, detail=f"Directory '{relative}' not found in official list"
    )


@router.post("/data-dirs/fix")
def fix_data_dirs():
    """Create any missing official directories (idempotent)."""
    mgr = DataDirManager(BASE_DIR)
    created = mgr.create_missing()
    return JSONResponse(
        content={
            "status": "success",
            "created": created,
            "count": len(created),
        }
    )


@router.post("/data-dirs/fix/{relative:path}")
def fix_data_dir(relative: str):
    """Create a single missing official directory."""
    mgr = DataDirManager(BASE_DIR)
    for d in mgr.official_dirs():
        if d.relative == relative:
            if not d.absolute.exists():
                d.absolute.mkdir(parents=True, exist_ok=True)
                return JSONResponse(
                    content={
                        "relative": relative,
                        "action": "created",
                        "ok": True,
                    }
                )
            return JSONResponse(
                content={
                    "relative": relative,
                    "action": "skip",
                    "ok": True,
                    "reason": "already exists",
                }
            )
    raise HTTPException(
        status_code=404, detail=f"Directory '{relative}' not found in official list"
    )


@router.post("/data-dirs/clean")
def clean_data_dirs():
    """Remove non-official directories and stray files under data/."""
    mgr = DataDirManager(BASE_DIR)
    removed = mgr.clean()
    return JSONResponse(
        content={
            "status": "success",
            "removed": removed,
            "count": len(removed),
        }
    )


@router.post("/data-dirs/hard-reset")
def hard_reset_data_dirs():
    """Delete the entire data/ tree and recreate the official structure.

    WARNING: This will permanently delete ALL data in the data/ directory.
    """
    mgr = DataDirManager(BASE_DIR)
    result = mgr.hard_reset()
    return JSONResponse(
        content={
            "status": "success",
            "removed_dirs": result["removed"],
            "created_dirs": result["created"],
        }
    )


# ────────────────────────────────────────────────────────────────
# Generic directory endpoints (legacy)
# ────────────────────────────────────────────────────────────────


class DirStatus(BaseModel):
    exists: bool
    path: str


class DirCreateRequest(BaseModel):
    path: str = "/"


def _clean_dir(p: Path) -> int:
    """Remove all contents from a directory, returning count of removed items."""
    count = 0
    if p.exists() and p.is_dir():
        for item in p.iterdir():
            try:
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
                count += 1
            except Exception:
                pass
    return count


@router.get("/directory", response_model=DirStatus)
def get_directory_status(path: str = "/"):
    """Check if a directory exists under BASE_DIR."""
    target = (BASE_DIR / Path(path).lstrip("/")).resolve()
    return DirStatus(exists=target.exists() and target.is_dir(), path=str(target))


@router.post("/directory", response_model=DirStatus)
def create_directory(req: DirCreateRequest):
    """Create a directory under BASE_DIR."""
    target = (BASE_DIR / Path(req.path).lstrip("/")).resolve()
    if not str(target).startswith(str(BASE_DIR)):
        raise HTTPException(status_code=400, detail="Invalid path")
    target.mkdir(parents=True, exist_ok=True)
    return DirStatus(exists=True, path=str(target))


@router.post("/directory/clean")
def clean_directory(req: DirCreateRequest):
    """Delete all contents inside a directory (except the directory itself)."""
    target = (BASE_DIR / Path(req.path).lstrip("/")).resolve()
    if not str(target).startswith(str(BASE_DIR)):
        raise HTTPException(status_code=400, detail="Invalid path")
    if not (target.exists() and target.is_dir()):
        return JSONResponse(content={"status": "ok", "message": "Directory does not exist"})
    removed = _clean_dir(target)
    return JSONResponse(
        content={"status": "ok", "message": "Directory cleaned", "items_removed": removed}
    )


@router.get("/data-folder", response_model=DirStatus)
def get_data_folder_status():
    """Check if the data folder exists."""
    return get_directory_status(path="/")


@router.post("/data-folder", response_model=DirStatus)
def create_data_folder():
    """Create the data folder if it doesn't exist."""
    return create_directory(DirCreateRequest(path="/"))


@router.post("/data-folder/clean")
def clean_data_folder():
    """Delete all contents inside BASE_DIR (except the folder itself)."""
    if not BASE_DIR.exists():
        return JSONResponse(content={"status": "ok", "message": "Data folder does not exist"})
    removed = _clean_dir(BASE_DIR)
    return JSONResponse(
        content={"status": "ok", "message": "Data folder cleaned", "items_removed": removed}
    )


# ────────────────────────────────────────────────────────────────
# DuckDB endpoint
# ────────────────────────────────────────────────────────────────


class DuckDBStatus(BaseModel):
    connected: bool
    path: str


@router.get("/duckdb", response_model=DuckDBStatus)
def get_duckdb_status():
    """Check if the DuckDB database file exists."""
    config = get_config()
    db_path = Path(config.paths_duckdb_path)
    return DuckDBStatus(connected=db_path.exists(), path=str(db_path))


@router.post("/duckdb", response_model=DuckDBStatus)
def create_duckdb():
    """Create the DuckDB database directory and an empty .duckdb file."""
    config = get_config()
    db_path = Path(config.paths_duckdb_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if not db_path.exists():
        db_path.touch()
    return DuckDBStatus(connected=True, path=str(db_path))


@router.post("/duckdb/clean")
def clean_duckdb():
    """Delete the DuckDB database file."""
    config = get_config()
    db_path = Path(config.paths_duckdb_path)
    if db_path.exists():
        db_path.unlink()
        return JSONResponse(content={"status": "ok", "message": "DuckDB database deleted"})
    return JSONResponse(content={"status": "ok", "message": "DuckDB database does not exist"})
