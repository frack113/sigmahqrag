"""Tests for llama.cpp health check."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.back.llamacpp.health import check_health


class TestCheckHealth:
    @pytest.mark.asyncio
    async def test_calls_shared_check(self) -> None:
        with patch("src.back.llamacpp.health._check", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {"status": "ok"}
            result = await check_health(timeout=5.0, port=8080)
            mock_check.assert_called_once_with(component="llama.cpp", port=8080, timeout=5.0)
            assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_default_port(self) -> None:
        with patch("src.back.llamacpp.health._check", new_callable=AsyncMock) as mock_check:
            mock_check.return_value = {"status": "ok"}
            result = await check_health()
            mock_check.assert_called_once_with(component="llama.cpp", port=8080, timeout=2.0)
            assert result == {"status": "ok"}
