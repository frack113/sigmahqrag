"""Tests for VRAM estimator wrapper (backward compatibility layer)."""

from unittest.mock import patch

from src.back.backend.services.vram import create_vram_estimator


class TestCreateVramEstimator:
    def test_creates_vram_estimator(self) -> None:
        with patch("src.back.backend.services.vram.VRAMEstimator") as mock:
            estimator = create_vram_estimator()
            mock.assert_called_once()
            assert estimator is mock.return_value
