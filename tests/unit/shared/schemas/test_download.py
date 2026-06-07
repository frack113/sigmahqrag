"""Tests for download schemas."""

from src.api.v1.models.schemas import (
    DownloadCancelRequest,
    DownloadCancelResponse,
    DownloadProgress,
    DownloadRequest,
    DownloadResponse,
)


class TestDownloadRequest:
    def test_init(self) -> None:
        req = DownloadRequest(service="llama.cpp", version="latest")
        assert req.service == "llama.cpp"
        assert req.version == "latest"


class TestDownloadResponse:
    def test_init(self) -> None:
        resp = DownloadResponse(
            download_id="abc-123",
            status="started",
            service="llama.cpp",
            version="b1234",
            target_path="/tmp/bin/llama.zip",
        )
        assert resp.download_id == "abc-123"
        assert resp.status == "started"
        assert resp.target_path == "/tmp/bin/llama.zip"


class TestDownloadProgress:
    def test_init(self) -> None:
        prog = DownloadProgress(
            percentage=50.0, bytes_downloaded=500, total_bytes=1000, speed_bps=10000
        )
        assert prog.percentage == 50.0
        assert prog.bytes_downloaded == 500
        assert prog.total_bytes == 1000
        assert prog.speed_bps == 10000


class TestDownloadCancelRequest:
    def test_init(self) -> None:
        req = DownloadCancelRequest(download_id="abc-123")
        assert req.download_id == "abc-123"


class TestDownloadCancelResponse:
    def test_init(self) -> None:
        resp = DownloadCancelResponse(download_id="abc-123", status="cancelled", message="Done")
        assert resp.download_id == "abc-123"
        assert resp.status == "cancelled"
        assert resp.message == "Done"
