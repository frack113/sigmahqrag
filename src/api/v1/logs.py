"""API endpoint to view system logs."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, StreamingResponse

from src.shared.config import get_config

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/logs", tags=["v1-logs"])


def get_logs_dir() -> Path:
    return Path(get_config().paths_logs_dir).resolve()


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


async def _tail_log_file(
    log_path: Path,
    lines: int = 50,
) -> str:
    """Read last N lines from log file."""
    if not log_path.exists():
        return _sse("error", "Log file not found")

    all_lines = read_log_file(log_path)
    if lines > 0:
        recent = all_lines[-lines:]
    entries = [line.strip() for line in recent]
    return _sse("init", entries, line_count=len(entries))


def _sse(event: str, data, **extra) -> str:
    payload = {"type": event}
    if isinstance(data, list):
        payload["lines"] = data
    else:
        payload["message"] = data
    payload.update(extra)
    return "event: log\n" + "data: " + json.dumps(payload) + "\n\n"


@router.get("/stream")
async def stream_logs(
    source: str = Query("system", description="Log source: system, llamacpp, qdrant"),
    lines: int = Query(default=50, ge=1, le=500),
):
    """SSE endpoint for live log streaming (tail -f)."""

    if source not in LOG_FILES:
        return JSONResponse(status_code=400, content={"error": f"Invalid log source: {source}"})

    # Resolve lines=0 as "all" for backwards compat
    effective_lines = lines if lines > 0 else 0

    logs_dir = get_logs_dir()
    log_filename = LOG_FILES[source]
    log_path = logs_dir / log_filename

    async def event_generator():
        # Track line counts to send only new lines
        init_msg = await _tail_log_file(log_path, lines=effective_lines)
        yield init_msg

        while True:
            try:
                await asyncio.sleep(1)
                if not log_path.exists():
                    yield _sse("error", "Log file deleted")
                    break

                all_lines = read_log_file(log_path)

                # Only yield lines beyond what was already sent
                total = len(all_lines)
                if effective_lines > 0:
                    recent = all_lines[-effective_lines:]
                else:
                    recent = all_lines
                new_entries = [line.strip() for line in recent]
                if new_entries:
                    yield _sse("update", new_entries, line_count=total)
            except asyncio.CancelledError:
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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

    if not source:
        source = "system"

    if source not in LOG_FILES:
        return JSONResponse(content={"logs": [], "message": f"Invalid log source: {source}"})

    logs_dir = get_logs_dir()
    log_filename = LOG_FILES[source]
    log_path = logs_dir / log_filename

    logger.info(f"Reading logs from: {log_path}, exists={log_path.exists()}")

    if not log_path.exists():
        return JSONResponse(content={"logs": [], "message": "Log file not found"})

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

        return JSONResponse(content={"logs": entries, "total": len(entries), "source": source})

    except Exception as e:
        import traceback

        logger.error(f"Failed to read logs: {e}\n{traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})


@router.delete("")
async def clear_logs(
    source: str = Query("", description="Log source to clear: system, llamacpp, qdrant"),
) -> JSONResponse:
    """Clear log file contents.

    Args:
        source: Log source (system, llamacpp, qdrant). Defaults to system.

    Returns:
        JSON with success status
    """

    if not source:
        source = "system"

    if source not in LOG_FILES:
        return JSONResponse(content={"success": False, "message": f"Invalid log source: {source}"})

    logs_dir = get_logs_dir()
    log_filename = LOG_FILES[source]
    log_path = logs_dir / log_filename

    try:
        if log_path.exists():
            with open(log_path, "w") as f:
                f.write("")
            logger.info(f"Cleared log file: {log_path}")
            return JSONResponse(content={"success": True, "message": f"Cleared {log_filename}"})
        return JSONResponse(content={"success": False, "message": "Log file does not exist"})
    except Exception as e:
        logger.error(f"Failed to clear logs: {e}")
        return JSONResponse(status_code=500, content={"error": "An internal error occurred"})
