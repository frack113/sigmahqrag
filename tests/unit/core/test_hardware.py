"""Tests for hardware detection module (Story 3.4 - RED phase)."""

from __future__ import annotations

import pytest

from src.core.hardware import check_model_compatibility, detect_hardware, get_hardware_report


class TestDetectHardware:
    """Test hardware detection functionality (AC1)."""

    @pytest.mark.asyncio
    async def test_detect_cpu_info(self):
        """Test CPU info detection (cores, threads)."""
        hardware = await detect_hardware()
        assert "cpu" in hardware
        assert "cores" in hardware["cpu"]
        assert "threads" in hardware["cpu"]
        assert hardware["cpu"]["cores"] > 0
        assert hardware["cpu"]["threads"] > 0

    @pytest.mark.asyncio
    async def test_detect_ram_info(self):
        """Test RAM info detection (total/available)."""
        hardware = await detect_hardware()
        assert "ram" in hardware
        assert "total" in hardware["ram"]
        assert "available" in hardware["ram"]
        assert hardware["ram"]["total"] > 0

    @pytest.mark.asyncio
    async def test_detect_gpu_info_when_available(self):
        """Test GPU detection if available."""
        hardware = await detect_hardware()
        # GPU may or may not be present - just check it's a dict if present
        if "gpu" in hardware:
            assert isinstance(hardware["gpu"], dict)

    @pytest.mark.asyncio
    async def test_hardware_detection_logged(self, caplog):
        """Test hardware info is logged (AC1)."""
        import logging
        with caplog.at_level(logging.INFO, logger="src.core.hardware"):
            await detect_hardware()
        assert "Hardware detected" in caplog.text or "CPU:" in caplog.text


class TestCheckModelCompatibility:
    """Test model compatibility validation (AC2)."""

    @pytest.mark.asyncio
    async def test_valid_gguf_model(self, tmp_path):
        """Test GGUF model format validation."""
        # Create a fake GGUF file
        model_file = tmp_path / "model.gguf"
        model_file.write_bytes(b"GGUF")  # Simplified GGUF header

        hardware = await detect_hardware()
        result = await check_model_compatibility(str(model_file), hardware)
        assert result["compatible"] is True
        assert result["format"] == "GGUF"

    @pytest.mark.asyncio
    async def test_invalid_model_format(self, tmp_path):
        """Test non-GGUF model rejection."""
        model_file = tmp_path / "model.bin"
        model_file.write_bytes(b"INVALID")

        hardware = await detect_hardware()
        result = await check_model_compatibility(str(model_file), hardware)
        assert result["compatible"] is False
        assert "format" in result or "error" in result

    @pytest.mark.asyncio
    async def test_model_memory_requirements(self, tmp_path):
        """Test model memory requirement validation."""
        model_file = tmp_path / "model.gguf"
        model_file.write_bytes(b"GGUF")

        hardware = await detect_hardware()
        result = await check_model_compatibility(str(model_file), hardware)
        assert "memory_required" in result
        assert "memory_available" in result


class TestGetHardwareReport:
    """Test hardware report endpoint data (AC3)."""

    @pytest.mark.asyncio
    async def test_report_returns_json_structure(self):
        """Test report returns proper JSON structure."""
        report = await get_hardware_report()
        assert "hardware" in report
        assert "model_compatibility" in report
        assert "status" in report

    @pytest.mark.asyncio
    async def test_report_response_time(self):
        """Test report returns within 200ms (AC3)."""
        import time
        start = time.time()
        await get_hardware_report()
        elapsed = (time.time() - start) * 1000
        assert elapsed < 200, f"Report took {elapsed}ms, expected <200ms"

    @pytest.mark.asyncio
    async def test_report_includes_compatibility_status(self):
        """Test report includes model compatibility status."""
        report = await get_hardware_report()
        # When no model configured, compatible should be None
        assert "compatible" in report["model_compatibility"]
        assert report["model_compatibility"]["compatible"] is None


class TestGracefulDegradation:
    """Test graceful degradation on detection failure (AC4)."""

    @pytest.mark.asyncio
    async def test_continues_with_defaults_on_failure(self, monkeypatch):
        """Test system continues with defaults if detection fails."""
        from src.core import hardware as hw_module

        def mock_virtual_memory_fail(*args, **kwargs):
            raise Exception("Detection failed")

        monkeypatch.setattr(hw_module.psutil, "virtual_memory", mock_virtual_memory_fail)

        # Should not raise, should return defaults
        hardware = await detect_hardware()
        assert hardware is not None
        assert "cpu" in hardware  # CPU detection should still work

    @pytest.mark.asyncio
    async def test_logs_warning_on_detection_failure(self, monkeypatch, caplog):
        """Test warning is logged on detection failure (AC4)."""
        import logging

        from src.core import hardware as hw_module

        def mock_cpu_count_fail(*args, **kwargs):
            raise Exception("CPU detection failed")

        monkeypatch.setattr(hw_module.psutil, "cpu_count", mock_cpu_count_fail)

        with caplog.at_level(logging.WARNING, logger="src.core.hardware"):
            await detect_hardware()
        assert "warning" in caplog.text.lower() or "failed" in caplog.text.lower()
