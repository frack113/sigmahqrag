"""Tests for VRAM estimator."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from src.infrastructure.llm.llamacpp.vram import VRAMEstimator, create_vram_estimator


class TestVRAMEstimator:
    def test_constructor_defaults(self) -> None:
        estimator = VRAMEstimator()
        assert estimator.overhead_coeff == 1.15
        assert estimator.buffer_mb == 512
        assert estimator._available_vram is None

    def test_constructor_custom(self) -> None:
        estimator = VRAMEstimator(overhead_coeff=1.5, buffer_mb=256)
        assert estimator.overhead_coeff == 1.5
        assert estimator.buffer_mb == 256

    @pytest.mark.asyncio
    async def test_estimate_approximated(self) -> None:
        estimator = VRAMEstimator()
        result = await estimator.estimate(model_size_bytes=1_000_000_000)
        assert result["is_approximation"] is True
        assert result["model_size_bytes"] == 1_000_000_000
        assert result["estimated_vram_bytes"] > 1_000_000_000
        assert "model_vram_bytes" in result["components"]
        assert "kv_cache_bytes" in result["components"]
        assert "buffer_bytes" in result["components"]

    @pytest.mark.asyncio
    async def test_estimate_precise(self) -> None:
        estimator = VRAMEstimator()
        result = await estimator.estimate(
            model_size_bytes=1_000_000_000,
            context_length=4096,
            layers=32,
            heads=32,
            head_dim=128,
        )
        assert result["is_approximation"] is False
        assert result["context_length"] == 4096

    @pytest.mark.asyncio
    async def test_get_available_vram_nvidia_success(self) -> None:
        estimator = VRAMEstimator()
        mock_process = type("Result", (), {"returncode": 0, "stdout": "8192\n"})()
        with patch("subprocess.run", return_value=mock_process):
            vram = await estimator.get_available_vram()
        assert vram == 8192 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_get_available_vram_nvidia_failure(self) -> None:
        estimator = VRAMEstimator()
        with patch("subprocess.run", side_effect=Exception("no GPU")):
            vram = await estimator.get_available_vram()
        assert vram == 8 * 1024 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_get_available_vram_already_known(self) -> None:
        estimator = VRAMEstimator()
        estimator._available_vram = 4 * 1024 * 1024 * 1024
        vram = await estimator.get_available_vram()
        assert vram == 4 * 1024 * 1024 * 1024

    @pytest.mark.asyncio
    async def test_check_compatibility_compatible(self) -> None:
        estimator = VRAMEstimator()
        estimator._available_vram = 10 * 1024 * 1024 * 1024
        result = await estimator.check_compatibility(model_size_bytes=1_000_000_000)
        assert result["is_compatible"] is True
        assert result["available_vram_gb"] == 10.0

    @pytest.mark.asyncio
    async def test_check_compatibility_incompatible(self) -> None:
        estimator = VRAMEstimator()
        estimator._available_vram = 1 * 1024 * 1024 * 1024
        result = await estimator.check_compatibility(model_size_bytes=2_000_000_000)
        assert result["is_compatible"] is False
        assert result["available_vram_bytes"] == 1 * 1024 * 1024 * 1024


class TestCreateVramEstimatorStandalone:
    def test_creates_vram_estimator(self) -> None:
        estimator = create_vram_estimator()
        assert isinstance(estimator, VRAMEstimator)
