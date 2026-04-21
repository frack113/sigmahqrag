"""VRAM estimation utilities."""

from __future__ import annotations

import json
import logging
import platform
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

QUANTIZATION_BITS: dict[str, float] = {
    "Q2": 2.5,
    "Q3": 3.5,
    "Q4": 4.5,
    "Q4_K_M": 4.5,
    "Q4_K_S": 4.25,
    "Q5": 5.5,
    "Q5_K_S": 5.5,
    "Q6": 6.5,
    "Q8": 8.0,
    "Q8_0": 8.0,
    "F16": 16.0,
    "F32": 32.0,
}

OVERHEAD_MULTIPLIER = 1.2


def get_available_vram() -> int | None:
    """Get available VRAM in bytes.

    Returns:
        Available VRAM in bytes, or None if undetectable
    """
    system = platform.system()

    if system == "Windows":
        return _get_nvidia_vram_windows()
    elif system == "Linux":
        return _get_nvidia_vram_linux()

    logger.warning("VRAM detection not supported on platform: %s", platform.system())
    return None


def _get_nvidia_vram_windows() -> int | None:
    """Get VRAM on Windows using nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            free_mb = int(result.stdout.strip().split("\n")[0])
            return free_mb * 1024 * 1024
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass

    return None


def _get_nvidia_vram_linux() -> int | None:
    """Get VRAM on Linux using nvidia-smi or rocm-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            free_mb = int(result.stdout.strip().split("\n")[0])
            return free_mb * 1024 * 1024
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError):
        pass

    try:
        result = subprocess.run(
            ["rocm-smi", "--query-gpu", "vram_free", "--json"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            free_bytes = data["card0"]["vram_free"]["bytes"]
            return free_bytes
    except (FileNotFoundError, subprocess.TimeoutExpired, ValueError, KeyError, json.JSONDecodeError):
        pass

    return None


def estimate_vram(model_params: int, quantization: str) -> int:
    """Estimate VRAM required for a model.

    Args:
        model_params: Number of parameters (e.g., 8_000_000_000 for 8B)
        quantization: Quantization level (e.g., Q4_K_M, F16)

    Returns:
        Estimated VRAM in bytes
    """
    bits_per_param = QUANTIZATION_BITS.get(quantization.upper(), 8.0)

    base_vram = (model_params * bits_per_param) / 8

    estimated = base_vram * OVERHEAD_MULTIPLIER

    return int(estimated)


def parse_model_size(model_name: str) -> int | None:
    """Parse model size from filename.

    Args:
        model_name: Model filename (e.g., llama-3.1-8b-q4_k_m.gguf)

    Returns:
        Number of parameters, or None if not detectable
    """
    model_lower = model_name.lower()

    size_patterns = [
        ("1b", 1_000_000_000),
        ("2b", 2_000_000_000),
        ("3b", 3_000_000_000),
        ("7b", 7_000_000_000),
        ("8b", 8_000_000_000),
        ("12b", 12_000_000_000),
        ("70b", 70_000_000_000),
        ("405b", 405_000_000_000),
    ]

    for pattern, params in size_patterns:
        if pattern in model_lower:
            return params

    return None


def get_vram_warning(estimated_vram: int, available_vram: int | None) -> str | None:
    """Check if VRAM estimate exceeds available.

    Args:
        estimated_vram: Estimated VRAM in bytes
        available_vram: Available VRAM in bytes

    Returns:
        Warning message if estimate > available, None otherwise
    """
    if available_vram is None:
        return None

    if estimated_vram > available_vram:
        est_gb = estimated_vram / (1024**3)
        avail_gb = available_vram / (1024**3)
        return f"⚠️ Warning: Estimated {est_gb:.1f}GB exceeds available {avail_gb:.1f}GB"

    return None


def format_vram(bytes_val: int) -> str:
    """Format bytes as human-readable string.

    Args:
        bytes_val: Bytes value

    Returns:
        Formatted string (e.g., "4.5 GB")
    """
    gb = bytes_val / (1024**3)
    return f"{gb:.1f} GB"


class VRAMEstimator:
    """VRAM estimation helper."""

    def __init__(self) -> None:
        """Initialize estimator."""
        self.available_vram = get_available_vram()

    def estimate(self, model_name: str, quantization: str) -> dict[str, Any]:
        """Estimate VRAM for a model.

        Args:
            model_name: Model filename
            quantization: Quantization level

        Returns:
            Dict with estimate and warnings
        """
        model_params = parse_model_size(model_name)

        if model_params is None:
            return {"error": "Could not detect model size from filename"}

        estimated = estimate_vram(model_params, quantization)

        warning = get_vram_warning(estimated, self.available_vram)

        return {
            "estimated_bytes": estimated,
            "estimated_formatted": format_vram(estimated),
            "available_bytes": self.available_vram,
            "available_formatted": format_vram(self.available_vram) if self.available_vram else "Unknown",
            "warning": warning,
        }
