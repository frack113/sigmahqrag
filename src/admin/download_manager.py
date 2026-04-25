"""Download manager for binary downloads from GitHub releases."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from src.admin.temp_manager import create_temp_manager
from src.admin.version_manager import (
    ReleaseAsset,
    VersionManager,
    create_version_manager,
)
from src.config import BIN_DIR
from src.exceptions import DownloadError

logger = logging.getLogger(__name__)


@dataclass
class DownloadTask:
    """Represents an active download task."""

    download_id: str
    service: str
    version: str
    asset: ReleaseAsset
    temp_path: Path
    target_path: Path
    status: str = "pending"
    bytes_downloaded: int = 0
    total_bytes: int = 0
    speed_bps: int = 0
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    progress_queue: asyncio.Queue | None = None


class DownloadManager:
    """Manager for downloading binaries from GitHub releases."""

    def __init__(
        self,
        version_manager: VersionManager | None = None,
        temp_manager_manager: Any | None = None,
    ) -> None:
        """Initialize download manager.

        Args:
            version_manager: Version manager for GitHub API
            temp_manager: Temp file manager
        """
        self.version_manager = version_manager or create_version_manager()
        self.temp_manager = temp_manager_manager or create_temp_manager()
        self.active_downloads: dict[str, DownloadTask] = {}
        self._cleanup_task: asyncio.Task | None = None

    async def start_download(
        self,
        service: str,
        version: str,
        github_token: str | None = None,
    ) -> dict[str, Any]:
        """Start a binary download.

        Args:
            service: Service name (llama.cpp, qdrant)
            version: Version tag or "latest"
            github_token: Optional GitHub token

        Returns:
            Dict with download_id, status, service, version, target_path
        """
        if service not in ("llama.cpp", "qdrant"):
            raise DownloadError(f"Unsupported service: {service}")

        release = await self.version_manager.get_release(service, version)

        asset = self.version_manager.find_matching_asset(release, service)
        if not asset:
            raise DownloadError(
                f"No matching binary found for {service} on this platform"
            )

        download_id = str(uuid.uuid4())
        temp_path = self.temp_manager.create_temp_file(download_id)
        target_path = BIN_DIR / f"{service.replace('.', '-')}"

        cancel_event = asyncio.Event()
        progress_queue = asyncio.Queue()

        download_task = DownloadTask(
            download_id=download_id,
            service=service,
            version=release.tag_name,
            asset=asset,
            temp_path=temp_path,
            target_path=target_path,
            status="started",
            total_bytes=asset.size,
            cancel_event=cancel_event,
            progress_queue=progress_queue,
        )

        self.active_downloads[download_id] = download_task

        asyncio.create_task(self._download_file(download_id, github_token))

        return {
            "download_id": download_id,
            "status": "started",
            "service": service,
            "version": release.tag_name,
            "target_path": str(target_path),
        }

    async def _download_file(
        self, download_id: str, github_token: str | None = None
    ) -> None:
        """Download a file with progress tracking.

        Args:
            download_id: Download ID
            github_token: Optional GitHub token
        """
        task = self.active_downloads.get(download_id)
        if not task:
            return

        headers = {}
        if github_token:
            headers["Authorization"] = f"Bearer {github_token}"

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(300.0, connect=30.0)
            ) as client:
                async with client.stream(
                    "GET",
                    task.asset.browser_download_url,
                    headers=headers,
                ) as response:
                    response.raise_for_status()

                    total = int(response.headers.get("content-length", 0))
                    task.total_bytes = total

                    downloaded = 0
                    start_time = asyncio.get_event_loop().time()
                    last_update = start_time
                    last_bytes = 0

                    with open(task.temp_path, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            if task.cancel_event.is_set():
                                logger.info(f"Download {download_id} cancelled")
                                task.status = "cancelled"
                                self.temp_manager.cleanup(task.temp_path)
                                if task.progress_queue:
                                    await task.progress_queue.put({
                                        "status": "cancelled",
                                    })
                                del self.active_downloads[download_id]
                                return

                            f.write(chunk)
                            downloaded += len(chunk)

                            current_time = asyncio.get_event_loop().time()
                            time_delta = current_time - last_update
                            if time_delta >= 0.5:
                                bytes_delta = downloaded - last_bytes
                                speed = int(bytes_delta / time_delta) if time_delta > 0 else 0
                                task.speed_bps = speed
                                last_update = current_time
                                last_bytes = downloaded
                                task.bytes_downloaded = downloaded

                            if task.progress_queue and time_delta >= 0.5:
                                await task.progress_queue.put({
                                    "percentage": (downloaded / total * 100) if total > 0 else 0,
                                    "bytes_downloaded": downloaded,
                                    "total_bytes": total,
                                    "speed_bps": task.speed_bps,
                                })
                                last_update = current_time

                    task.status = "completed"
                    task.bytes_downloaded = downloaded
                    task.temp_path.rename(task.target_path)
                    os.chmod(task.target_path, 0o755)

                    if task.progress_queue:
                        await task.progress_queue.put({
                            "status": "completed",
                            "file_path": str(task.target_path),
                        })

                    logger.info(
                        f"Download {download_id} completed: {task.target_path}"
                    )

        except Exception as e:
            logger.error(f"Download {download_id} failed: {e}")
            task.status = "failed"
            self.temp_manager.cleanup(task.temp_path)
            if task.progress_queue:
                await task.progress_queue.put({
                    "status": "failed",
                    "error": str(e),
                })

    async def cancel_download(self, download_id: str) -> dict[str, Any]:
        """Cancel an active download.

        Args:
            download_id: Download ID to cancel

        Returns:
            Dict with download_id, status, message
        """
        task = self.active_downloads.get(download_id)
        if not task:
            return {
                "download_id": download_id,
                "status": "not_found",
                "message": f"Download {download_id} not found",
            }

        if task.status not in ("started", "pending"):
            return {
                "download_id": download_id,
                "status": task.status,
                "message": f"Download already {task.status}",
            }

        task.cancel_event.set()
        task.status = "cancelled"

        return {
            "download_id": download_id,
            "status": "cancelled",
            "message": "Download cancelled and partial file cleaned up",
        }

    def get_progress(self, download_id: str) -> DownloadTask | None:
        """Get download task for progress tracking.

        Args:
            download_id: Download ID

        Returns:
            DownloadTask or None
        """
        return self.active_downloads.get(download_id)

    def get_progress_stream(
        self, download_id: str
    ) -> asyncio.Queue | None:
        """Get progress queue for SSE streaming.

        Args:
            download_id: Download ID

        Returns:
            asyncio.Queue or None
        """
        task = self.active_downloads.get(download_id)
        if task:
            return task.progress_queue
        return None


_download_manager: DownloadManager | None = None


def create_download_manager() -> DownloadManager:
    """Create a download manager instance."""
    global _download_manager
    if _download_manager is None:
        _download_manager = DownloadManager()
    return _download_manager
