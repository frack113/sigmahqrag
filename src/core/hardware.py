"""Hardware detection module (Story 3.4 - GREEN phase)."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import psutil


def detect_hardware() -> dict[str, Any]:
    """Detect hardware capabilities (AC1, AC4, NFR14).

    Returns hardware profile with CPU, RAM, and optional GPU info.
    Gracefully handles detection failures with defaults.
    """
    hardware: dict[str, Any] = {}

    try:
        # CPU detection
        cores = psutil.cpu_count(logical=False) or 1
        threads = psutil.cpu_count(logical=True) or cores
        freq = psutil.cpu_freq()

        hardware["cpu"] = {
            "cores": cores,
            "threads": threads,
            "freq_mhz": int(freq.current) if freq else 0,
        }
    except Exception:
        hardware["cpu"] = {"cores": 1, "threads": 1, "freq_mhz": 0}
        hardware["cpu_error"] = "Detection failed"

    try:
        # RAM detection
        memory = psutil.virtual_memory()
        hardware["ram"] = {
            "total_gb": memory.total // (1024**3),
            "available_gb": memory.available // (1024**3),
        }
    except Exception:
        hardware["ram"] = {"total_gb": 0, "available_gb": 0}
        hardware["ram_error"] = "Detection failed"

    # GPU detection (optional, platform-specific)
    try:
        gpu_info = _detect_gpu()
        if gpu_info:
            hardware["gpu"] = gpu_info
    except Exception:
        pass  # GPU detection is optional

    return hardware


def _detect_gpu() -> dict[str, Any] | None:
    """Detect GPU capabilities (optional)."""
    # Placeholder for GPU detection logic
    # Could use torch.cuda.is_available() or similar in Growth phase
    return None


def check_model_compatibility(
    model_path: str, hardware: dict[str, Any]
) -> dict[str, Any]:
    """Check if model is compatible with hardware (AC2).

    Args:
        model_path: Path to GGUF model file
        hardware: Hardware profile from detect_hardware()

    Returns:
        Dict with 'compatible' bool and optional 'error' or 'reason'
    """
    if not model_path:
        return {"compatible": False, "error": "Empty model path"}

    path = Path(model_path)

    if not path.exists():
        return {"compatible": False, "error": "Model file not found"}

    if path.suffix.lower() != ".gguf":
        return {"compatible": False, "error": "Not a GGUF model"}

    try:
        model_size = path.stat().st_size
        available_ram = hardware.get("ram", {}).get("available_gb", 0)

        # Rough estimate: model needs at least 1.5x its size in RAM
        required_gb = (model_size * 1.5) / (1024**3)

        if required_gb > available_ram:
            return {
                "compatible": False,
                "reason": f"Model requires ~{required_gb:.1f}GB, only {available_ram}GB available",
            }

        return {"compatible": True, "model_size_gb": model_size / (1024**3)}

    except Exception as e:
        return {"compatible": False, "error": str(e)}


async def get_hardware_report() -> dict[str, Any]:
    """Get comprehensive hardware report (AC3).

    Returns hardware profile with optional model compatibility status.
    Response time <200ms for AC3.
    """
    loop = asyncio.get_event_loop()

    # Run hardware detection in thread pool to avoid blocking
    hardware = await loop.run_in_executor(None, detect_hardware)

    report: dict[str, Any] = {
        "cpu": hardware.get("cpu", {}),
        "ram": hardware.get("ram", {}),
    }

    if "gpu" in hardware:
        report["gpu"] = hardware["gpu"]

    # Model compatibility check (if model configured)
    model_path = _get_configured_model()
    if model_path:
        compatibility = check_model_compatibility(model_path, hardware)
        report["model"] = compatibility

    return report


def _get_configured_model() -> str | None:
    """Get configured model path from environment or config.

    TODO Growth: Read from config file or environment variable.
    """
    # Placeholder - model path would come from config
    return None
