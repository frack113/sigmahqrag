"""Model selection component."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import gradio as gr

DEFAULT_MODELS_DIR = "models/llm"


def scan_models(models_dir: str = DEFAULT_MODELS_DIR) -> list[tuple[str, str]]:
    """Scan directory for available GGUF models.

    Args:
        models_dir: Path to models directory

    Returns:
        List of tuples (repo_id, filename)
    """
    registry_path = Path("models/registry.json")
    if not registry_path.exists():
        return []

    import json

    with open(registry_path) as f:
        data = json.load(f)

    models = []
    for repo_id, record in data.get("models", {}).items():
        files = record.get("files", {})
        if not files:
            continue
        for filename in files.keys():
            if filename.endswith(".gguf"):
                models.append((f"{repo_id}/{filename}", f"{repo_id} - {filename}"))

    return sorted(models, key=lambda x: x[1])


def get_model_info(repo_id: str, filename: str) -> dict[str, Any]:
    """Get model information.

    Args:
        repo_id: HuggingFace repo ID
        filename: Model filename

    Returns:
        Dict with model info (size, quantization)
    """
    registry_path = Path("models/registry.json")
    if not registry_path.exists():
        return {"error": "Registry not found"}

    import json

    with open(registry_path) as f:
        data = json.load(f)

    record = data.get("models", {}).get(repo_id)
    if not record:
        return {"error": "Model not found in registry"}

    files = record.get("files", {})
    file_data = files.get(filename)
    if not file_data:
        return {"error": "File not found"}

    file_size = file_data.get("file_size", 0)
    quantization = detect_quantization(filename)

    return {
        "repo_id": repo_id,
        "filename": filename,
        "size_bytes": file_size,
        "size_mb": file_size / (1024 * 1024),
        "quantization": quantization,
    }


def detect_quantization(filename: str) -> str:
    """Detect quantization type from model filename.

    Args:
        filename: Model filename

    Returns:
        Quantization type (e.g., Q4_K_M, Q8_0, F16)
    """
    model_lower = filename.lower()

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
    choices = [m[1] for m in models]

    return gr.Dropdown(
        choices=choices,
        label="Select Model",
        value=choices[0] if choices else "",
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
    repo_id = info.get("repo_id", "")
    filename = info.get("filename", "")

    return f"""**Model:** {repo_id}

- **File:** {filename}
- **Size:** {size_mb:.1f} MB
- **Quantization:** {quantization}
"""
