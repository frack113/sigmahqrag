"""Pure functions for Sigma rule detection and reference extraction."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml

from src.core.sigma.models import is_sigma_rule as is_sigma_rule_fn


def is_sigma_rule(file_path: Path) -> bool:
    """Check if a YAML file is a Sigma rule.

    Re-export of the canonical ``is_sigma_rule`` from
    ``src.core.sigma.models`` for the ``Path``-only call-signature.
    """
    return is_sigma_rule_fn(file_path)


def extract_sigma_references(file_path: Path) -> list[str]:
    """Extract reference URLs from a Sigma rule's ``references`` field."""
    try:
        data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return []
        refs = data.get("references", [])
        if not isinstance(refs, list):
            return []
        return [str(r) for r in refs if r]
    except Exception:
        return []


def get_sigma_rule_id(file_path: Path) -> Optional[str]:
    """Extract the Sigma rule UUID from the ``id`` field if present."""
    try:
        data = yaml.safe_load(file_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        rule_id: str | None = data.get("id")
        if rule_id and isinstance(rule_id, str):
            return rule_id
    except Exception:
        pass
    return None
