"""Shared SSE progress generator for download streams."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

from src.config.settings import get_config
from src.shared.download_manager import create_download_manager


async def download_progress_generator(
    download_id: str,
    terminal_statuses: frozenset[str] = frozenset({"completed", "cancelled", "failed"}),
    timeout: float | None = None,
) -> AsyncGenerator[str, None]:
    """Generate SSE progress updates for a download.

    Args:
        download_id: The download identifier.
        terminal_statuses: Statuses that terminate the stream.
        timeout: Seconds between progress updates before timeout.
                 Falls back to ``sse_timeout`` from config if not set.

    Yields:
        SSE-formatted progress events.
    """
    if timeout is None:
        timeout = getattr(get_config(), "sse_timeout", 60.0)

    manager = create_download_manager()
    queue = manager.get_progress_stream(download_id)

    if not queue:
        yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
        return

    while True:
        try:
            data = await asyncio.wait_for(queue.get(), timeout=timeout)
            yield f"data: {json.dumps(data)}\n\n"

            if data.get("status") in terminal_statuses:
                break
        except TimeoutError:
            yield f"data: {json.dumps({'status': 'timeout'})}\n\n"
            break
