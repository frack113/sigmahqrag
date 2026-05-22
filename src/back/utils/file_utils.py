from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_registry_files(registry_path: Path) -> list[dict[str, Any]]:
    """
    Loads the registry from a JSON file and returns a list of entries.
    Each entry is a dictionary containing the metadata for a file.
    """
    if not registry_path.exists():
        return []

    with open(registry_path, encoding="utf-8") as f:
        registry_data = json.load(f)

    # The registry is a dict where keys are hashes and values are metadata
    # We embed the hash and filename into each entry
    entries: list[dict[str, Any]] = []
    for key, value in registry_data.items():
        entry = dict(value)
        entry["hash"] = key
        entry["file_name"] = f"{key}.md"
        entry["path"] = f"{key}.md"
        entries.append(entry)
    return entries
