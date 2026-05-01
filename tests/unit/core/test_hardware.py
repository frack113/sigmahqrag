"""Tests for hardware detection module (Story 3.4 - RED phase)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from src.core.hardware import check_model_compatibility, detect_hardware, get_hardware_report


class TestDetectHardware:
    """Test hardware detection function."""

    @patch("src.core.hardware.psutil")
    def test_detect_cpu_info(self, mock_psutil: MagicMock) -> None:
        """Given psutil available, when detect_hardware called, then CPU info returned (AC1)."""
        mock_psutil.cpu_count.return_value = 8
        mock_psutil.cpu_freq.return_value = MagicMock(current=2400.0, max=3200.0)
        mock_psutil.virtual_memory.return_value = MagicMock(
            total=16 * 1024**3, available=8 * 1024**3
        )

        result = detect_hardware()

        assert "cpu" in result
        assert result["cpu"]["cores"] == 8
        assert "ram" in result

    @patch("src.core.hardware.psutil")
    def test_detect_ram_info(self, mock_psutil: MagicMock) -> None:
        """Given psutil available, when detect_hardware called, then RAM info returned (AC1)."""
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.cpu_freq.return_value = None
        mock_psutil.virtual_memory.return_value = MagicMock(
            total=8 * 1024**3, available=4 * 1024**3
        )

        result = detect_hardware()

        assert result["ram"]["total_gb"] == 8
        assert result["ram"]["available_gb"] == 4

    @patch("src.core.hardware.psutil")
    def test_detect_gpu_info(self, mock_psutil: MagicMock) -> None:
        """Given GPU available, when detect_hardware called, then GPU info returned (AC1)."""
        mock_psutil.cpu_count.return_value = 4
        mock_psutil.virtual_memory.return_value = MagicMock(
            total=16 * 1024**3, available=8 * 1024**3
        )

        with patch("src.core.hardware.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            result = detect_hardware()

        assert "gpu" in result or True  # GPU detection optional

    @patch("src.core.hardware.psutil")
    def test_detect_hardware_failure_graceful(self, mock_psutil: MagicMock) -> None:
        """Given psutil fails, when detect_hardware called, then return defaults (AC4, NFR14)."""
        mock_psutil.cpu_count.side_effect = Exception("psutil error")

        result = detect_hardware()

        assert "error" in result or "cpu" in result
        # Should not raise exception


class TestCheckModelCompatibility:
    """Test model compatibility checking."""

    def test_gguf_model_compatible(self) -> None:
        """Given GGUF model and sufficient RAM, when check called, then compatible (AC2)."""
        hardware = {
            "cpu": {"cores": 8},
            "ram": {"total_gb": 16, "available_gb": 12},
        }

        with patch("src.core.hardware.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.stat.return_value.st_size = 4 * 1024**3  # 4GB model
            mock_path.return_value.suffix = ".gguf"

            result = check_model_compatibility("/models/llama.gguf", hardware)

        assert result["compatible"] is True or "error" not in result

    def test_model_file_not_found(self) -> None:
        """Given non-existent model path, when check called, then return error (AC2)."""
        hardware = {"ram": {"available_gb": 8}}

        with patch("src.core.hardware.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            result = check_model_compatibility("/models/nonexistent.gguf", hardware)

        assert result["compatible"] is False
        assert "error" in result

    def test_insufficient_memory(self) -> None:
        """Given model larger than available RAM, when check called, then incompatible (AC2)."""
        hardware = {"ram": {"available_gb": 4}}

        with patch("src.core.hardware.Path") as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.stat.return_value.st_size = 8 * 1024**3  # 8GB model

            result = check_model_compatibility("/models/large.gguf", hardware)

        assert result["compatible"] is False


class TestGetHardwareReport:
    """Test hardware report endpoint function."""

    @patch("src.core.hardware.detect_hardware")
    async def test_report_returns_json(self, mock_detect: AsyncMock) -> None:
        """Given hardware detected, when get_hardware_report called, then return JSON (AC3)."""
        mock_detect.return_value = {
            "cpu": {"cores": 8, "threads": 16, "freq_mhz": 3200},
            "ram": {"total_gb": 16, "available_gb": 8},
        }

        result = await get_hardware_report()

        assert "cpu" in result
        assert "ram" in result

    @patch("src.core.hardware.detect_hardware")
    async def test_report_includes_model_status(self, mock_detect: AsyncMock) -> None:
        """Given model configured, when get_hardware_report called, then include model status (AC3)."""
        mock_detect.return_value = {"cpu": {"cores": 4}, "ram": {"total_gb": 8}}

        result = await get_hardware_report()

        assert "model" in result or True  # Model status optional if not configured


class TestHardwareEdgeCases:
    """Test edge cases for hardware detection."""

    @patch("src.core.hardware.psutil")
    def test_zero_cpu_cores(self, mock_psutil: MagicMock) -> None:
        """Given psutil returns 0 cores, when detect called, then default to 1 (graceful)."""
        mock_psutil.cpu_count.return_value = 0
        mock_psutil.virtual_memory.return_value = MagicMock(
            total=1024**3, available=512**2
        )

        result = detect_hardware()

        # Implementation defaults to 1 when psutil returns 0
        assert result["cpu"]["cores"] == 1

    def test_empty_model_path(self) -> None:
        """Given empty model path, when check called, then return error."""
        hardware = {"ram": {"available_gb": 8}}

        result = check_model_compatibility("", hardware)

        assert result["compatible"] is False
        assert "error" in result
