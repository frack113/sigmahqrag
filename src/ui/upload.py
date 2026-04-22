"""YAML upload component."""

from __future__ import annotations

import logging
import os

import gradio as gr
import yaml

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 1_000_000


def create_upload_button() -> gr.UploadButton:
    """Create YAML upload button."""
    return gr.UploadButton(
        label="Upload Sigma Rule (YAML)",
        file_count="single",
        file_types=[".yaml", ".yml"],
    )


async def process_uploaded_file(file: dict[str, str] | None) -> str:
    """Process uploaded YAML file.

    Args:
        file: Uploaded file dict with path

    Returns:
        Parsed YAML content as string or error message
    """
    if not file:
        return "No file uploaded"

    try:
        file_size = os.path.getsize(file["path"])
        if file_size > MAX_FILE_SIZE:
            return f"File too large. Maximum size is {MAX_FILE_SIZE} bytes."

        with open(file["path"], encoding="utf-8") as f:
            content = yaml.safe_load(f)

        if not content:
            return "Empty YAML file"

        return yaml.dump(content, default_flow_style=False)

    except yaml.YAMLError as e:
        logger.error(f"YAML parse error: {e}")
        return f"Invalid YAML: {e}"
    except Exception as e:
        logger.error(f"File read error: {e}")
        return f"Error reading file: {e}"
