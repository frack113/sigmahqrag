"""Hardware detection module (Story 3.4 - GREEN phase)."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import psutil

logger = logging.getLogger(__name__)


async def detect_hardware() -> dict[str, Any]:
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
        logger.info(f"CPU: {cores} cores, {threads} threads")
    except Exception as e:
        logger.warning(f"CPU detection failed: {e}")
        hardware["cpu"] = {"cores": 1, "threads": 1, "freq_mhz": 0}
        hardware["cpu_error"] = "Detection failed"

    try:
        # RAM detection - keys match test expectations
        memory = psutil.virtual_memory()
        hardware["ram"] = {
            "total": memory.total,
            "available": memory.available,
        }
        logger.info(f"RAM: {hardware['ram']['total'] // (1024**3)}GB total")
    except Exception as e:
        logger.warning(f"RAM detection failed: {e}")
        hardware["ram"] = {"total": 0, "available": 0}
        hardware["ram_error"] = "Detection failed"

    # GPU detection (optional, returns None if not available)
    try:
        gpu_info = _detect_gpu()
        if gpu_info:
            hardware["gpu"] = gpu_info
    except Exception as e:
        logger.debug(f"GPU detection failed: {e}")
        # GPU detection is optional

    logger.info("Hardware detected")
    return hardware


def _detect_gpu() -> dict[str, Any] | None:
    """Detect GPU capabilities (optional).

    Returns GPU info dict or None if not available.
    """
    try:
        # Try to detect NVIDIA GPU via nvidia-smi (Windows/Linux)
        import subprocess

        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.free",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0 and result.stdout.strip():
            lines = result.stdout.strip().split("\n")
            if lines:
                parts = lines[0].split(",")
                if len(parts) >= 3:
                    return {
                        "name": parts[0].strip(),
                        "memory_total_mb": int(parts[1].strip()),
                        "memory_free_mb": int(parts[2].strip()),
                    }
    except Exception:
        pass
    return None


async def check_model_compatibility(
    model_path: str, hardware: dict[str, Any]
) -> dict[str, Any]:
    """Check if model is compatible with hardware (AC2).

    Args:
        model_path: Path to GGUF model file
        hardware: Hardware profile from detect_hardware()

    Returns:
        Dict with 'compatible' bool, 'format', and memory info
    """
    if not model_path:
        return {"compatible": False, "error": "Empty model path"}

    path = Path(model_path)

    if not path.exists():
        return {"compatible": False, "error": "Model file not found"}

    if path.suffix.lower() != ".gguf":
        return {
            "compatible": False,
            "format": path.suffix.lower(),
            "error": "Not a GGUF model",
        }

    try:
        model_size = path.stat().st_size
        available_ram = hardware.get("ram", {}).get("available", 0)

        # Rough estimate: model needs at least 1.5x its size in RAM
        required_bytes = model_size * 1.5
        required_gb = required_bytes / (1024**3)
        available_gb = available_ram / (1024**3)

        if required_bytes > available_ram:
            return {
                "compatible": False,
                "format": "GGUF",
                "memory_required": required_gb,
                "memory_available": available_gb,
                "reason": f"Model requires ~{required_gb:.1f}GB, only {available_gb:.1f}GB available",
            }

        return {
            "compatible": True,
            "format": "GGUF",
            "memory_required": required_gb,
            "memory_available": available_gb,
            "model_size_gb": model_size / (1024**3),
        }

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
        "hardware": hardware,
        "status": "ok",
    }

    # Model compatibility check (if model configured)
    model_path = _get_configured_model()
    if model_path:
        compatibility = await check_model_compatibility(model_path, hardware)
        report["model_compatibility"] = compatibility
    else:
        report["model_compatibility"] = {
            "compatible": None,
            "message": "No model configured",
        }

    return report


def _get_configured_model() -> str | None:
    """Get configured model path from environment or config.

    TODO Growth: Read from config file or environment variable.
    """
    # Placeholder - model path would come from config
    return None
