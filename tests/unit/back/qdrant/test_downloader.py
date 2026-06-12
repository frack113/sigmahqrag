"""Tests for QdrantInstallerService (streaming, injectable client, progress)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.infrastructure.vectorstore.downloader import (
    QdrantInstallerService,
    create_qdrant_installer,
)


class TestQdrantInstallerServiceInit:
    def test_creates_with_default_config(self) -> None:
        installer = create_qdrant_installer()
        assert installer.bin_dir is not None
        assert installer.static_dir is not None

    def test_injects_http_client(self) -> None:
        client = httpx.AsyncClient()
        installer = QdrantInstallerService(http_client=client)
        assert installer._client is client

    def test_get_client_returns_injected(self) -> None:
        client = httpx.AsyncClient()
        installer = QdrantInstallerService(http_client=client)
        assert installer._get_client() is client

    def test_get_client_creates_default(self) -> None:
        installer = QdrantInstallerService()
        client = installer._get_client()
        assert client is not None
        assert isinstance(client, httpx.AsyncClient)


class TestStreamToFile:
    @pytest.mark.asyncio
    async def test_streams_to_file(self, tmp_path: Path) -> None:
        async def aiter_bytes():
            yield b"chunk1"
            yield b"chunk2"
            yield b"c"

        mock_response = MagicMock()
        mock_response.headers = {"content-length": "9"}
        mock_response.aiter_bytes = aiter_bytes
        mock_response.raise_for_status = MagicMock()

        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.__aenter__.return_value = mock_client
        mock_client.stream.return_value = mock_stream

        dest = tmp_path / "test.zip"
        installer = QdrantInstallerService(http_client=mock_client)
        await installer._stream_to_file("http://example.com/file.zip", dest)

        assert dest.read_bytes() == b"chunk1chunk2c"

    @pytest.mark.asyncio
    async def test_retries_on_http_error(self, tmp_path: Path) -> None:
        attempt_counter = 0

        class FailingResponse:
            def __init__(self) -> None:
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            @property
            def headers(self):
                return {"content-length": "4"}

            def raise_for_status(self) -> None:
                nonlocal attempt_counter
                attempt_counter += 1
                if attempt_counter == 1:
                    raise httpx.HTTPStatusError(
                        "Server error", request=MagicMock(), response=MagicMock()
                    )

            async def aiter_bytes(self):
                yield b"data"

        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = FailingResponse()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.__aenter__.return_value = mock_client
        mock_client.stream.return_value = mock_stream

        dest = tmp_path / "retry.zip"
        installer = QdrantInstallerService(http_client=mock_client)
        await installer._stream_to_file("http://example.com/file.zip", dest)

        assert dest.read_bytes() == b"data"
        assert attempt_counter == 2

    @pytest.mark.asyncio
    async def test_progress_callback_invoked(self, tmp_path: Path) -> None:
        async def aiter_bytes():
            yield b"x" * 10

        mock_response = MagicMock()
        mock_response.headers = {"content-length": "10"}
        mock_response.aiter_bytes = aiter_bytes
        mock_response.raise_for_status = MagicMock()

        mock_stream = AsyncMock()
        mock_stream.__aenter__.return_value = mock_response

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.__aenter__.return_value = mock_client
        mock_client.stream.return_value = mock_stream

        progress_values: list[int] = []
        progress_messages: list[str] = []

        def cb(pct: int, msg: str) -> None:
            progress_values.append(pct)
            progress_messages.append(msg)

        dest = tmp_path / "prog.zip"
        installer = QdrantInstallerService(http_client=mock_client)
        await installer._stream_to_file(
            "http://example.com/file.zip", dest, cb, pct_before=5, pct_after=45
        )

        assert len(progress_values) > 0
        assert 5 <= progress_values[0] <= 45


class TestDownloadBinary:
    @pytest.mark.asyncio
    async def test_download_binary_integration(self, tmp_path: Path) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        zip_path = tmp_path / "qdrant.zip"

        installer = QdrantInstallerService(
            bin_dir=tmp_path,
            http_client=mock_client,
        )

        async def fake_stream(url: str, dest: Path, *args, **kwargs) -> None:
            dest.write_bytes(b"fake zip content")

        with (
            patch.object(installer, "_stream_to_file", side_effect=fake_stream),
            patch.object(installer, "_safe_extract_zip") as mock_extract,
        ):
            result = await installer.download_binary()

            assert result["success"] is True
            mock_extract.assert_called_once_with(zip_path, tmp_path)

    @pytest.mark.asyncio
    async def test_download_binary_http_error(self, tmp_path: Path) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)

        installer = QdrantInstallerService(
            bin_dir=tmp_path,
            http_client=mock_client,
        )

        with patch.object(installer, "_get_client") as mock_get_client:
            mock_get_client.side_effect = httpx.HTTPError("Connection failed")

            result = await installer.download_binary()

            assert result["success"] is False
            assert "error" in result


class TestDownloadWebUi:
    @pytest.mark.asyncio
    async def test_download_web_ui_integration(self, tmp_path: Path) -> None:
        static_dir = tmp_path / "static"
        static_dir.mkdir(parents=True)

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        installer = QdrantInstallerService(
            bin_dir=tmp_path,
            static_dir=static_dir,
            http_client=mock_client,
        )

        async def fake_stream(url: str, dest: Path, *args, **kwargs) -> None:
            dest.write_bytes(b"fake zip content")

        with (
            patch.object(installer, "_stream_to_file", side_effect=fake_stream),
            patch.object(installer, "_safe_extract_zip"),
        ):
            result = await installer.download_web_ui()

            assert result["success"] is True


class TestClose:
    @pytest.mark.asyncio
    async def test_close_aclient(self) -> None:
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        installer = QdrantInstallerService(http_client=mock_client)
        await installer.close()
        mock_client.aclose.assert_awaited_once()
        assert installer._client is None

    @pytest.mark.asyncio
    async def test_close_no_client(self) -> None:
        installer = QdrantInstallerService()
        await installer.close()
