"""Download manager for binary downloads from GitHub releases."""

from __future__ import annotations

import asyncio
import logging
import shutil
import uuid
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx

from src.shared import BIN_DIR
from src.shared.exceptions import DownloadError
from src.shared.temp_manager import create_temp_manager
from src.shared.version_manager import (
    ReleaseAsset,
    VersionManager,
    create_version_manager,
)

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
    post_install_callback: Any | None = None


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
        post_install_callback: Any | None = None,
    ) -> dict[str, Any]:
        """Start a binary download.

        Args:
            service: Service name (llama.cpp, qdrant)
            version: Version tag or "latest"
            github_token: Optional GitHub token
            post_install_callback: Async callback to run after installation
        """

        if service not in ("llama.cpp", "qdrant"):
            raise DownloadError(f"Unsupported service: {service}")

        # Check if requested version is already installed
        if version == "latest":
            release = await self.version_manager.get_release(service, version)
            version_to_check = release.tag_name.lstrip("v")
        else:
            version_to_check = version.lstrip("v")

        if service in ("llama", "llama.cpp"):
            from src.shared import get_llamacpp_version

            current_version = get_llamacpp_version()
        elif service in ("qdrant", "qdrant_db"):
            from src.shared import get_qdrant_version

            current_version = get_qdrant_version()
        else:
            current_version = None

        if current_version and current_version == version_to_check:
            logger.info(f"Version {version_to_check} already installed for {service}")
            return {
                "download_id": None,
                "status": "skipped",
                "service": service,
                "version": version_to_check,
                "message": "Version already installed",
            }

        release = await self.version_manager.get_release(service, version)

        asset = self.version_manager.find_matching_asset(release, service)
        if not asset:
            raise DownloadError(
                f"No matching binary found for {service} on this platform"
            )

        download_id = str(uuid.uuid4())
        file_ext = ".zip" if asset.name.endswith(".zip") else ".tar.gz"
        temp_path = self.temp_manager.create_temp_file(download_id, extension=file_ext)
        target_path = BIN_DIR / f"{service.replace('.', '-')}{file_ext}"

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
            post_install_callback=post_install_callback,
        )

        self.active_downloads[download_id] = download_task

        asyncio.create_task(self._download_file(download_id, github_token))

        return {
            "download_id": download_id,
            "status": "started",
            "service": service,
            "version": release.tag_name,
            "file_name": asset.name,
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
                timeout=httpx.Timeout(300.0, connect=30.0),
                follow_redirects=True,
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
                                    await task.progress_queue.put(
                                        {"status": "cancelled"}
                                    )
                                del self.active_downloads[download_id]
                                return

                            f.write(chunk)
                            downloaded += len(chunk)

                            current_time = asyncio.get_event_loop().time()
                            time_delta = current_time - last_update
                            if time_delta >= 0.5:
                                bytes_delta = downloaded - last_bytes
                                speed = (
                                    int(bytes_delta / time_delta)
                                    if time_delta > 0
                                    else 0
                                )
                                task.speed_bps = speed
                                last_update = current_time
                                last_bytes = downloaded
                                task.bytes_downloaded = downloaded

                            if task.progress_queue and time_delta >= 0.5:
                                await task.progress_queue.put(
                                    {
                                        "percentage": (
                                            (downloaded / total * 100)
                                            if total > 0
                                            else 0
                                        ),
                                        "bytes_downloaded": downloaded,
                                        "total_bytes": total,
                                        "speed_bps": task.speed_bps,
                                    }
                                )
                                last_update = current_time

                    task.status = "completed"
                    task.bytes_downloaded = downloaded
                    BIN_DIR.mkdir(parents=True, exist_ok=True)

                    await self._extract_and_install(
                        task.temp_path, task.target_path, task.service
                    )

                    if task.post_install_callback:
                        await task.post_install_callback(task.target_path)

                    if task.progress_queue:
                        await task.progress_queue.put(
                            {
                                "status": "completed",
                                "file_path": str(task.target_path),
                            }
                        )

                    version_str = task.version.lstrip("v")

                    if task.service in ("llama", "llama.cpp"):
                        from src.shared import set_llamacpp_version

                        set_llamacpp_version(version_str)
                    elif task.service in ("qdrant", "qdrant_db"):
                        from src.shared import set_qdrant_version

                        set_qdrant_version(version_str)

                    logger.info(f"Download {download_id} completed: {task.target_path}")

        except Exception as e:
            logger.error(f"Download {download_id} failed: {e}")
            task.status = "failed"
            self.temp_manager.cleanup(task.temp_path)
            if task.progress_queue:
                await task.progress_queue.put(
                    {
                        "status": "failed",
                        "error": str(e),
                    }
                )

    async def _extract_and_install(
        self, temp_path: Path, target_path: Path, service: str
    ) -> None:
        """Extract archive and install to bin directory.

        Args:
            temp_path: Path to downloaded archive
            target_path: Target path for the service binary/directory
            service: Service name (llama.cpp, qdrant)
        """
        import subprocess

        service_dir = BIN_DIR / service.replace(".", "-")

        # Clean up existing service directory
        if service_dir.exists():
            try:
                # On Windows, first try to remove read-only files
                for item in service_dir.rglob("*"):
                    try:
                        if item.is_file():
                            item.chmod(0o777)
                    except Exception:
                        pass
                shutil.rmtree(service_dir)
                logger.info(f"Cleaned existing directory: {service_dir}")
            except Exception as e:
                logger.warning(f"Could not clean {service_dir}: {e}")
                # Try alternative: rename old dir and create new one
                try:
                    import time

                    old_dir = service_dir.with_suffix(f".old.{int(time.time())}")
                    service_dir.rename(old_dir)
                    logger.info(f"Renamed old dir to {old_dir}")
                except Exception:
                    pass

        # Create fresh directory
        service_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created service directory: {service_dir}")

        try:
            BIN_DIR.mkdir(parents=True, exist_ok=True)

            if temp_path.suffix == ".zip":
                logger.info(f"Extracting ZIP: {temp_path}")
                # Extract to a temp location first
                import tempfile

                with tempfile.TemporaryDirectory() as tmp_dir:
                    with zipfile.ZipFile(temp_path, "r") as zf:
                        zf.extractall(tmp_dir)

                    # Find the top-level directory in the zip
                    items = list(Path(tmp_dir).iterdir())
                    logger.info(
                        f"ZIP contains {len(items)} items: {[i.name for i in items]}"
                    )
                    if len(items) == 1 and items[0].is_dir():
                        # Single directory - copy contents to service_dir
                        extracted_dir = items[0]
                        logger.info(f"Copying from subdirectory: {extracted_dir.name}")
                        for f in extracted_dir.iterdir():
                            dst = service_dir / f.name
                            logger.info(f"Copying {f.name} to {dst}")
                            if f.is_file():
                                shutil.copy2(f, dst)
                            elif f.is_dir():
                                shutil.copytree(f, dst, dirs_exist_ok=True)
                        logger.info(
                            f"Copied files from {extracted_dir.name} to {service_dir}"
                        )
                    else:
                        # Direct files - copy to service_dir
                        for f in items:
                            dst = service_dir / f.name
                            if f.is_file():
                                shutil.copy2(f, dst)
                            elif f.is_dir():
                                shutil.copytree(f, dst, dirs_exist_ok=True)
                logger.info(f"Extracted to: {service_dir}")

            else:
                # tar.gz handling
                import tempfile

                with tempfile.TemporaryDirectory() as tmp_dir:
                    result = subprocess.run(
                        ["tar", "-xf", str(temp_path), "-C", tmp_dir],
                        capture_output=True,
                        text=True,
                    )
                    if result.returncode != 0:
                        raise RuntimeError(f"Failed to extract tar.gz: {result.stderr}")

                    # Find the top-level directory
                    items = list(Path(tmp_dir).iterdir())
                    logger.info(
                        f"TAR.GZ contains {len(items)} items: {[i.name for i in items]}"
                    )
                    if len(items) == 1 and items[0].is_dir():
                        extracted_dir = items[0]
                        logger.info(f"Copying from subdirectory: {extracted_dir.name}")
                        for f in extracted_dir.iterdir():
                            dst = service_dir / f.name
                            logger.info(f"Copying {f.name} to {dst}")
                            if f.is_file():
                                shutil.copy2(f, dst)
                            elif f.is_dir():
                                shutil.copytree(f, dst, dirs_exist_ok=True)
                        logger.info(
                            f"Copied files from {extracted_dir.name} to {service_dir}"
                        )
                    else:
                        # Direct files
                        for f in Path(tmp_dir).iterdir():
                            dst = service_dir / f.name
                            if f.is_file():
                                shutil.copy2(f, dst)
                            elif f.is_dir():
                                shutil.copytree(f, dst, dirs_exist_ok=True)
                logger.info(f"Extracted tar.gz to: {service_dir}")

            # Verify extraction success
            if not service_dir.exists():
                raise RuntimeError(f"Extraction failed: {service_dir} does not exist")

            logger.info(f"Successfully installed {service} to {service_dir}")

        except Exception as e:
            logger.error(f"Extraction failed for {service}: {e}")
            # Clean up partial extraction
            if service_dir.exists():
                try:
                    shutil.rmtree(service_dir)
                except Exception:
                    pass
            raise

        finally:
            self.temp_manager.cleanup(temp_path)
            logger.info(f"Cleaned temp file: {temp_path}")

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

    def get_progress_stream(self, download_id: str) -> asyncio.Queue | None:
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
