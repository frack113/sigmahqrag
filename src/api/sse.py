"""Shared SSE progress generator for download streams."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator

from src.shared.download_manager import create_download_manager


async def download_progress_generator(
    download_id: str,
    terminal_statuses: frozenset[str] = frozenset({"completed", "cancelled", "failed"}),
) -> AsyncGenerator[str, None]:
    """Generate SSE progress updates for a download.

    Args:
        download_id: The download identifier.
        terminal_statuses: Statuses that terminate the stream.

    Yields:
        SSE-formatted progress events.
    """
    manager = create_download_manager()
    queue = manager.get_progress_stream(download_id)

    if not queue:
        yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
        return

    while True:
        try:
            data = await asyncio.wait_for(queue.get(), timeout=30.0)
            yield f"data: {json.dumps(data)}\n\n"

            if data.get("status") in terminal_statuses:
                break
        except TimeoutError:
            yield f"data: {json.dumps({'status': 'timeout'})}\n\n"
            break
