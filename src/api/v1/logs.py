"""API endpoint to view system logs."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/logs", tags=["v1-logs"])


def get_logs_dir() -> Path:
    base = os.environ.get("DATA_DIR", "data")
    return Path(base) / "logs"


LOG_FILES = {
    "system": "sigmahqrag.log",
    "llamacpp": "llama.cpp.log",
    "qdrant": "qdrant.log",
}

ENCODING_OPTIONS = ["utf-8", "latin-1", "cp1252", "ascii"]


def read_log_file(path: Path) -> list[str]:
    for encoding in ENCODING_OPTIONS:
        try:
            with open(path, encoding=encoding, errors="strict") as f:
                return f.readlines()
        except UnicodeDecodeError:
            continue
    with open(path, encoding="utf-8", errors="replace") as f:
        return f.readlines()


@router.get("")
async def get_logs(
    source: str = Query("", description="Log source: system, llamacpp, qdrant"),
    lines: int = Query(default=0, ge=0, le=500),
    level: str = Query(default="", description="Filter by level: INFO, WARNING, ERROR"),
) -> JSONResponse:
    """Get recent log entries.

    Args:
        source: Log source (system, llamacpp, qdrant)
        lines: Number of lines (default from config)
        level: Filter by level (INFO, WARNING, ERROR)

    Returns:
        JSON with log entries
    """
    from src.share import load_config

    if not source:
        source = load_config().get("logging", {}).get("display_source", "system")

    if not lines:
        lines = load_config().get("logging", {}).get("display_nb_line", 25)

    if not level:
        level = load_config().get("logging", {}).get("display_level", "")

    logs_dir = get_logs_dir()
    log_filename = LOG_FILES.get(source, LOG_FILES["system"])
    log_path = logs_dir / log_filename

    logger.info(f"Reading logs from: {log_path}, exists={log_path.exists()}")

    if not log_path.exists():
        return JSONResponse(
            content={"logs": [], "message": f"Log file not found: {log_path}"}
        )

    try:
        all_lines = read_log_file(log_path)

        if level:
            filtered = [line for line in all_lines if f" {level}:" in line]
        else:
            filtered = all_lines

        recent = filtered[-lines:]

        entries = []
        for line in recent:
            entries.append({"text": line.strip()})

        return JSONResponse(
            content={"logs": entries, "total": len(entries), "source": source}
        )

    except Exception as e:
        import traceback

        logger.error(f"Failed to read logs: {e}\n{traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"error": str(e)})
