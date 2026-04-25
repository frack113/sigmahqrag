"""Tests for VRAM estimation."""

from unittest.mock import patch

import pytest


class TestQuantBytes:
    """Test quantization bytes table."""

    def test_q4_k_m_bytes(self):
        """Test Q4_K_M quantization."""
        from src.ui.vram import QUANT_BYTES

        assert QUANT_BYTES["Q4_K_M"] == 2.5

    def test_f16_bytes(self):
        """Test F16 quantization."""
        from src.ui.vram import QUANT_BYTES

        assert QUANT_BYTES["F16"] == 6.0


class TestEstimateVRAM:
    """Test VRAM estimation."""

    def test_estimate_q4_k_m(self):
        """Test VRAM estimation for Q4_K_M."""
        from src.ui.vram import estimate_vram

        vram = estimate_vram(8.0, "Q4_K_M")
        assert vram == 8.0 * 2.5 * 1.2

    def test_estimate_f16(self):
        """Test VRAM estimation for F16."""
        from src.ui.vram import estimate_vram

        vram = estimate_vram(8.0, "F16")
        assert vram == 8.0 * 6.0 * 1.2


class TestEstimateModelParams:
    """Test model parameter estimation."""

    def test_8b_model(self):
        """Test 8B model estimation."""
        from src.ui.vram import estimate_model_params

        params = estimate_model_params(8 * 1024**3)
        assert params == pytest.approx(10.67, rel=0.1)


class TestCheckVRAMFit:
    """Test VRAM fit check."""

    def test_fits_in_vram(self):
        """Test model fits in available VRAM."""
        from src.ui.vram import check_vram_fit

        result = check_vram_fit(512 * 1024**2, "Q4_K_M", available_vram=10.0)
        assert result["fits"] is True
        assert result["available_vram_gb"] == 10.0

    def test_does_not_fit_in_vram(self):
        """Test model doesn't fit in available VRAM."""
        from src.ui.vram import check_vram_fit

        result = check_vram_fit(8 * 1024**3, "Q4_K_M", available_vram=4.0)
        assert result["fits"] is False
        assert "warning" in result


class TestGetAvailableVRAM:
    """Test VRAM detection."""

    @patch("subprocess.run")
    def test_nvidia_smi_detects(self, mock_run):
        """Test nvidia-smi detection."""
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "8192\n"

        from src.ui.vram import get_available_vram

        vram = get_available_vram()
        assert vram == 8.0

    @patch("subprocess.run")
    def test_nvidia_smi_unavailable(self, mock_run):
        """Test nvidia-smi not available."""
        mock_run.side_effect = FileNotFoundError()

        from src.ui.vram import get_available_vram

        vram = get_available_vram()
        assert vram is None
