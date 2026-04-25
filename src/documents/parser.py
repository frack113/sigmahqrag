"""Sigma rule parser."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from src.documents.models import SigmaRule

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {"title", "detection", "condition"}
MAX_FILE_SIZE = 1024 * 1024


def parse_yaml_file(file_path: str) -> dict[str, Any]:
    """Parse a YAML file.

    Args:
        file_path: Path to YAML file

    Returns:
        Parsed YAML content as dictionary

    Raises:
        yaml.YAMLError: If YAML is invalid
        FileNotFoundError: If file doesn't exist
        ValueError: If file is too large or wrong extension
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.suffix.lower() not in (".yml", ".yaml"):
        raise ValueError(f"Invalid file extension: {path.suffix}")

    size = path.stat().st_size
    if size > MAX_FILE_SIZE:
        raise ValueError(f"File too large: {size} bytes (max {MAX_FILE_SIZE})")

    with open(file_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_sigma_rule(file_path: str) -> SigmaRule | None:
    """Parse a Sigma rule from YAML file.

    Args:
        file_path: Path to Sigma rule YAML file

    Returns:
        SigmaRule instance or None if parsing fails

    Raises:
        ValueError: If required fields missing
    """
    try:
        data = parse_yaml_file(file_path)
    except (yaml.YAMLError, FileNotFoundError, ValueError):
        return None

    if not isinstance(data, dict):
        logger.warning(f"Invalid YAML structure in {file_path}")
        return None

    for field in REQUIRED_FIELDS:
        if field not in data:
            logger.warning(f"Missing required field '{field}' in {file_path}")
            return None

    rule_id = data.get("id", "")
    if not rule_id:
        rule_id = os.path.splitext(os.path.basename(file_path))[0]

    try:
        return SigmaRule(
            id=rule_id,
            title=data.get("title", ""),
            detection=data.get("detection", {}),
            condition=data.get("condition", ""),
            description=data.get("description"),
            author=data.get("author"),
            date=data.get("date"),
            modified=data.get("modified"),
            references=data.get("references", []),
            tags=data.get("tags", []),
            level=data.get("level"),
            falsepositives=data.get("falsepositives", []),
            logsource=data.get("logsource", {}),
            status=data.get("status"),
            license=data.get("license"),
        )
    except Exception as e:
        logger.warning(f"Failed to create SigmaRule: {e}")
        return None


def scan_directory(directory: str, recursive: bool = True) -> list[str]:
    """Scan directory for Sigma rule files.

    Args:
        directory: Directory to scan
        recursive: Whether to scan subdirectories

    Returns:
        List of YAML file paths
    """
    dir_path = Path(directory)

    if not dir_path.exists() or not dir_path.is_dir():
        return []

    pattern = "**/*.y*ml" if recursive else "*.y*ml"
    files = sorted(dir_path.glob(pattern))

    return [str(f) for f in files if f.is_file()]
