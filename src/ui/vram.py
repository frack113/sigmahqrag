"""VRAM estimation for LLM models."""

from __future__ import annotations

import logging
import subprocess
from typing import Any

logger = logging.getLogger(__name__)

QUANT_BYTES = {
    "Q2_K": 1.0,
    "Q3_K_S": 1.2,
    "Q3_K_M": 1.4,
    "Q4_K_S": 2.0,
    "Q4_K_M": 2.5,
    "Q5_K_S": 2.8,
    "Q5_K_M": 3.0,
    "Q6_K": 3.5,
    "Q8_0": 4.0,
    "F16": 6.0,
    "F32": 12.0,
}

OVERHEAD_FACTOR = 1.2


def get_available_vram() -> float | None:
    """Get available VRAM in GB.

    Returns:
        Available VRAM in GB, or None if unable to detect
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return float(result.stdout.strip().split("\n")[0]) / 1024
    except Exception as e:
        logger.debug(f"nvidia-smi not available: {e}")

    try:
        result = subprocess.run(
            ["rocm-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return float(result.stdout.strip().split("\n")[0]) / 1024
    except Exception as e:
        logger.debug(f"rocm-smi not available: {e}")

    return None


def estimate_vram(model_params: float, quantization: str) -> float:
    """Estimate VRAM requirement for a model.

    Args:
        model_params: Number of parameters in billions
        quantization: Quantization type (e.g., Q4_K_M)

    Returns:
        Estimated VRAM in GB
    """
    bytes_per_param = QUANT_BYTES.get(quantization, 4.0)
    return model_params * bytes_per_param * OVERHEAD_FACTOR


def estimate_model_params(model_size_bytes: int) -> float:
    """Estimate model parameters from file size.

    Args:
        model_size_bytes: Model file size in bytes

    Returns:
        Estimated number of parameters in billions
    """
    size_gb = model_size_bytes / (1024**3)
    return size_gb / 0.75


def check_vram_fit(
    model_size_bytes: int,
    quantization: str = "Q4_K_M",
    available_vram: float | None = None,
) -> dict[str, Any]:
    """Check if model fits in VRAM.

    Args:
        model_size_bytes: Model file size in bytes
        quantization: Quantization type
        available_vram: Available VRAM in GB (auto-detect if None)

    Returns:
        Dict with fit status and warnings
    """
    if available_vram is None:
        available_vram = get_available_vram()

    params = estimate_model_params(model_size_bytes)
    estimated_vram = estimate_vram(params, quantization)

    result: dict[str, Any] = {
        "model_params": params,
        "quantization": quantization,
        "estimated_vram_gb": estimated_vram,
    }

    if available_vram is not None:
        result["available_vram_gb"] = available_vram
        result["fits"] = estimated_vram <= available_vram
        if not result["fits"]:
            result["warning"] = (
                f"Model requires ~{estimated_vram:.1f}GB VRAM, "
                f"but only {available_vram:.1f}GB available"
            )
    else:
        result["available_vram_gb"] = None
        result["fits"] = True
        result["warning"] = "Unable to detect VRAM - model may not fit"

    return result
