from __future__ import annotations

import json
from pathlib import Path

def load_registry_files(registry_path: Path) -> list[dict[str, any]]:
    """
    Loads the registry from a JSON file and returns a list of entries.
    Each entry is a dictionary containing the metadata for a file.
    """
    if not registry_path.exists():
        return []

    with open(registry_path, "r", encoding="utf-8") as f:
        registry_data = json.load(f)

    # The registry is a dict where keys are hashes and values are metadata
    # We return a list of the values (the metadata)
    return list(registry_data.values())
