"""GitHub backend package."""

from __future__ import annotations

from .api import (
    download_release_file,
    info_release,
    list_release_files,
    list_releases,
)
from .git import (
    clone_repo,
    delete_repo,
    get_metadata,
    list_repos,
    save_metadata,
    update_repo,
)

__all__ = [
    # GitHub API
    "list_releases",
    "info_release",
    "list_release_files",
    "download_release_file",
    # Git local
    "clone_repo",
    "update_repo",
    "delete_repo",
    "list_repos",
    "save_metadata",
    "get_metadata",
]
