"""Download schemas for binary downloads."""

from __future__ import annotations

from pydantic import BaseModel


class DownloadRequest(BaseModel):
    """Request model for downloading binaries."""

    service: str
    version: str


class DownloadResponse(BaseModel):
    """Response model for download initiation."""

    download_id: str
    status: str
    service: str
    version: str
    target_path: str


class DownloadProgress(BaseModel):
    """Progress model for SSE updates."""

    percentage: float
    bytes_downloaded: int
    total_bytes: int
    speed_bps: int


class DownloadCancelRequest(BaseModel):
    """Request model for cancelling a download."""

    download_id: str


class DownloadCancelResponse(BaseModel):
    """Response model for download cancellation."""

    download_id: str
    status: str
    message: str
