"""Quantization configuration and utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .vram import estimate_vram


@dataclass(frozen=True)
class QuantizationLevel:
    """Quantization level configuration."""

    name: str
    bits_per_param: float
    description: str


QUANTIZATION_LEVELS: dict[str, QuantizationLevel] = {
    "Q2": QuantizationLevel(
        name="Q2",
        bits_per_param=2.5,
        description="Smallest size, lowest quality",
    ),
    "Q4_K_M": QuantizationLevel(
        name="Q4_K_M",
        bits_per_param=4.5,
        description="Recommended balance (default)",
    ),
    "Q5_K_S": QuantizationLevel(
        name="Q5_K_S",
        bits_per_param=5.5,
        description="Better quality, moderate size",
    ),
    "Q8_0": QuantizationLevel(
        name="Q8_0",
        bits_per_param=8.0,
        description="Near-float quality",
    ),
    "F16": QuantizationLevel(
        name="F16",
        bits_per_param=16.0,
        description="Full float16 (highest quality)",
    ),
}


def get_quantization_options() -> list[str]:
    """Get list of available quantization options.

    Returns:
        List of quantization level names
    """
    return list(QUANTIZATION_LEVELS.keys())


def get_quantization_info(quant_name: str, model_params: int) -> dict[str, Any]:
    """Get quantization info with VRAM estimate.

    Args:
        quant_name: Quantization level name
        model_params: Model parameter count

    Returns:
        Dict with quantization details and VRAM estimate
    """
    if quant_name not in QUANTIZATION_LEVELS:
        return {"error": f"Unknown quantization: {quant_name}"}

    quant = QUANTIZATION_LEVELS[quant_name]
    vram_estimate = estimate_vram(model_params, quant_name)

    return {
        "name": quant.name,
        "bits_per_param": quant.bits_per_param,
        "description": quant.description,
        "vram_bytes": vram_estimate,
        "vram_gb": vram_estimate / (1024**3),
    }


def create_quantization_dropdown() -> list[tuple[str, str]]:
    """Create choices for quantization dropdown.

    Returns:
        List of (value, label) tuples
    """
    choices = []
    for name, quant in QUANTIZATION_LEVELS.items():
        bits = quant.bits_per_param
        choices.append((name, f"{name} ({bits} bits/param)"))
    return choices


def suggest_quantization(available_vram: int | None, model_params: int) -> str | None:
    """Suggest quantization based on available VRAM.

    Args:
        available_vram: Available VRAM in bytes
        model_params: Model parameter count

    Returns:
        Recommended quantization level or None
    """
    if available_vram is None:
        return "Q4_K_M"

    for quant_name in ["Q8_0", "Q5_K_S", "Q4_K_M", "Q2"]:
        needed = estimate_vram(model_params, quant_name)
        if needed <= available_vram:
            return quant_name

    return "Q2"
