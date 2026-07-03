"""Path resolution helpers for Sigma reference documents.

Handles mapping between logical paths (content_type, file_name) and
physical filesystem paths for the sigmaref storage layout.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.shared.utils.identify_file_type import filetype_subdir


def subdir_for(content_type: str | None) -> str:
    """Return the subdirectory name for a given content type.

    Args:
        content_type: Content type string (e.g. "markdown", "pdf").

    Returns:
        Subdirectory name (e.g. "markdown").
    """
    return filetype_subdir(content_type or "")


def sigmaref_write_path(output_path: Path, content_type: str | None, file_name: str) -> Path:
    """Compute the write path for a sigmaref document.

    Args:
        output_path: Base output directory.
        content_type: Content type of the document.
        file_name: Name of the file.

    Returns:
        Full path where the file should be written.
    """
    return output_path / subdir_for(content_type) / file_name


def sigmaref_resolve_path(output_path: Path, content_type: str | None, file_name: str) -> Path:
    """Resolve the actual path for a sigmaref document (handles existing files).

    Args:
        output_path: Base output directory.
        content_type: Content type of the document.
        file_name: Name of the file.

    Returns:
        Path that exists or should be created.
    """
    candidate = sigmaref_write_path(output_path, content_type, file_name)
    if candidate.exists():
        return candidate
    return output_path / file_name


def resolve_rule_path(entry: dict, cfg: Any) -> Path | None:
    """Resolve the on-disk path for a rule entry.

    Args:
        entry: Registry entry with org, repo, file_name fields.
        cfg: Configuration object.

    Returns:
        Path to the rule file, or None if not found.
    """
    org: str = entry.get("org", "") or ""
    repo: str = entry.get("repo", "") or ""
    file_name: str = entry.get("file_name", "") or ""

    if org == "local":
        return Path(cfg.local_documents_path).resolve() / file_name

    if org == "sigmaref":
        base = Path(cfg.sigmaref_documents_path).resolve()
        subdir = filetype_subdir(entry.get("content_type", ""))
        candidate = base / subdir / file_name
        if candidate.exists():
            return candidate
        return base / file_name

    if org and repo:
        return Path(cfg.paths_github_dir).resolve() / org / repo / file_name

    return None
