from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _resolve_file_path(registry_dir: Path, key: str) -> Path:
    """Resolve a registry key to its actual file path, trying any extension."""
    candidates = sorted(registry_dir.glob(f"{key}.*"))
    if candidates:
        return candidates[0]
    return registry_dir / f"{key}.md"


def load_registry_files(registry_path: Path) -> list[dict[str, Any]]:
    """
    Loads the registry from a JSON file and returns a list of entries.
    Each entry is a dictionary containing the metadata for a file.
    """
    if not registry_path.exists():
        return []

    with open(registry_path, encoding="utf-8") as f:
        registry_data = json.load(f)

    registry_dir = registry_path.parent

    entries: list[dict[str, Any]] = []
    for key, value in registry_data.items():
        resolved = _resolve_file_path(registry_dir, key)
        entry = dict(value)
        entry["hash"] = key
        entry["file_name"] = resolved.name
        entry["path"] = str(resolved)
        entries.append(entry)
    return entries
