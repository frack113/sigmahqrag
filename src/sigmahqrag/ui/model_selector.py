"""Model selection component."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import gradio as gr

DEFAULT_MODELS_DIR = "models/llm"


def scan_models(models_dir: str = DEFAULT_MODELS_DIR) -> list[str]:
    """Scan directory for available GGUF models.

    Args:
        models_dir: Path to models directory

    Returns:
        List of model names (filenames without extension)
    """
    if not os.path.exists(models_dir):
        return []

    models = []
    for f in os.listdir(models_dir):
        f_lower = f.lower()
        if f_lower.endswith(".gguf"):
            ext_len = len(".gguf")
            model_name = f[:-ext_len]
            models.append(model_name)

    return sorted(models)


def get_model_info(
    model_name: str, models_dir: str = DEFAULT_MODELS_DIR
) -> dict[str, Any]:
    """Get model information.

    Args:
        model_name: Name of the model
        models_dir: Path to models directory

    Returns:
        Dict with model info (size, quantization)
    """
    model_path = Path(models_dir) / f"{model_name}.gguf"

    if not model_path.exists():
        return {"error": "Model not found"}

    file_size = model_path.stat().st_size

    quantization = detect_quantization(model_name)

    return {
        "name": model_name,
        "size_bytes": file_size,
        "size_mb": file_size / (1024 * 1024),
        "quantization": quantization,
    }


def detect_quantization(model_name: str) -> str:
    """Detect quantization type from model filename.

    Args:
        model_name: Model filename

    Returns:
        Quantization type (e.g., Q4_K_M, Q8_0, F16)
    """
    model_lower = model_name.lower()

    patterns = [
        ("q2_k", "Q2_K"),
        ("q3_k_s", "Q3_K_S"),
        ("q3_k_m", "Q3_K_M"),
        ("q4_k_s", "Q4_K_S"),
        ("q4_k_m", "Q4_K_M"),
        ("q5_k_s", "Q5_K_S"),
        ("q5_k_m", "Q5_K_M"),
        ("q6_k", "Q6_K"),
        ("q8_0", "Q8_0"),
        ("q2", "Q2"),
        ("q3", "Q3"),
        ("q4", "Q4"),
        ("q5", "Q5"),
        ("q6", "Q6"),
        ("q8", "Q8"),
        ("f16", "F16"),
        ("f32", "F32"),
    ]

    for pattern, quant in patterns:
        if pattern in model_lower:
            return quant

    return "Unknown"


def create_model_dropdown(
    models_dir: str = DEFAULT_MODELS_DIR,
) -> gr.Dropdown:
    """Create model selection dropdown.

    Args:
        models_dir: Path to models directory

    Returns:
        Gradio Dropdown component
    """
    models = scan_models(models_dir)

    return gr.Dropdown(
        choices=models,
        label="Select Model",
        value=models[0] if models else "",
    )


def create_model_info_component() -> gr.Markdown:
    """Create model info display component.

    Returns:
        Gradio Markdown component
    """
    return gr.Markdown(
        value="Select a model to view info",
        label="Model Info",
    )


def format_model_info(info: dict[str, Any]) -> str:
    """Format model info for display.

    Args:
        info: Model info dict

    Returns:
        Formatted markdown string
    """
    if "error" in info:
        return f"**Error:** {info['error']}"

    size_mb = info.get("size_mb", 0)
    quantization = info.get("quantization", "Unknown")

    return f"""**Model:** {info["name"]}

- **Size:** {size_mb:.1f} MB
- **Quantization:** {quantization}"""
