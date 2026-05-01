"""Tests for hardware detection module."""

import pytest
from src.core.hardware import check_model_compatibility, detect_hardware, get_hardware_report

class TestDetectHardware:
    @pytest.mark.asyncio
    async def test_detect_cpu_info(self):
        hardware = detect_hardware()
        assert "cpu" in hardware

class TestCheckModelCompatibility:
    @pytest.mark.asyncio
    async def test_valid_gguf_model(self, tmp_path):
        model_file = tmp_path / "model.gguf"
        model_file.write_bytes(b"GGUF")
        hardware = detect_hardware()
        result = await check_model_compatibility(str(model_file), hardware)
        assert result["compatible"] is True

class TestGetHardwareReport:
    @pytest.mark.asyncio
    async def test_report_returns_json_structure(self):
        report = await get_hardware_report()
        assert "hardware" in report

class TestGracefulDegradation:
    @pytest.mark.asyncio
    async def test_continues_with_defaults_on_failure(self, monkeypatch):
        from src.core import hardware as hw_module
        def mock_fail(*args, **kwargs): raise Exception("fail")
        monkeypatch.setattr(hw_module.psutil, "virtual_memory", mock_fail)
        hardware = detect_hardware()
        assert "cpu" in hardware
