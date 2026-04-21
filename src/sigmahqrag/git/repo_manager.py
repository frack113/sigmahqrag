"""Git repository management."""

from __future__ import annotations

import logging
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from git import Repo

logger = logging.getLogger(__name__)

DEFAULT_REPOS_DIR = "data/repos"
LOCKFILE = ".cloning"


class RepositoryManager:
    """Manage Git repositories."""

    def __init__(self, repos_dir: str = DEFAULT_REPOS_DIR) -> None:
        """Initialize repository manager.

        Args:
            repos_dir: Directory to store repositories
        """
        self.repos_dir = Path(repos_dir)
        self.repos_dir.mkdir(parents=True, exist_ok=True)

    def clone(
        self,
        url: str,
        name: str | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Clone a Git repository.

        Args:
            url: Git repository URL
            name: Optional name for the repository (defaults to repo name)
            progress: Optional callback for progress updates

        Returns:
            Dict with clone status and info
        """
        if name is None:
            name = self._extract_repo_name(url)

        dest_path = self.repos_dir / name

        if dest_path.exists():
            if not self._is_valid_repo(dest_path):
                shutil.rmtree(dest_path, ignore_errors=True)
            else:
                return {
                    "success": False,
                    "error": f"Repository '{name}' already exists",
                }

        lockfile = dest_path / LOCKFILE
        if lockfile.exists():
            return {
                "success": False,
                "error": f"Repository '{name}' is currently being cloned",
            }

        try:
            lockfile.touch()

            def progress_callback(remote_msg: str) -> None:
                if progress:
                    progress(remote_msg)
                logger.debug(f"Clone progress: {remote_msg}")

            Repo.clone_from(url, dest_path, progress_fn=progress_callback)
            logger.info(f"Cloned repository: {url} -> {dest_path}")

            lockfile.unlink(missing_ok=True)

            return {
                "success": True,
                "name": name,
                "path": str(dest_path),
            }
        except Exception as e:
            logger.error(f"Failed to clone {url}: {e}")
            if dest_path.exists():
                shutil.rmtree(dest_path, ignore_errors=True)
            lockfile.unlink(missing_ok=True)
            return {
                "success": False,
                "error": str(e),
            }

    def _is_valid_repo(self, path: Path) -> bool:
        """Check if a path is a valid Git repository.

        Args:
            path: Path to check

        Returns:
            True if valid Git repo
        """
        git_dir = path / ".git"
        return git_dir.exists() and (git_dir.is_dir() or git_dir.is_file())

    def list_repos(self) -> list[dict[str, Any]]:
        """List all cloned repositories.

        Returns:
            List of repository info dicts
        """
        repos = []
        for item in self.repos_dir.iterdir():
            if item.is_dir() and self._is_valid_repo(item):
                repos.append({
                    "name": item.name,
                    "path": str(item),
                })
        return sorted(repos, key=lambda r: r["name"])

    def delete(self, name: str) -> dict[str, Any]:
        """Delete a repository.

        Args:
            name: Repository name

        Returns:
            Dict with delete status
        """
        repo_path = self.repos_dir / name

        if not repo_path.exists():
            return {
                "success": False,
                "error": f"Repository '{name}' not found",
            }

        try:
            shutil.rmtree(repo_path)
            logger.info(f"Deleted repository: {name}")
            return {
                "success": True,
            }
        except Exception as e:
            logger.error(f"Failed to delete {name}: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_repo_path(self, name: str) -> Path | None:
        """Get path to a repository.

        Args:
            name: Repository name

        Returns:
            Path to repository or None if not found
        """
        repo_path = self.repos_dir / name
        if repo_path.exists() and (repo_path / ".git").exists():
            return repo_path
        return None

    def _extract_repo_name(self, url: str) -> str:
        """Extract repository name from URL.

        Args:
            url: Git URL (HTTP, HTTPS, SSH, or file path)

        Returns:
            Repository name
        """
        url = url.rstrip("/")

        if url.endswith(".git"):
            url = url[:-4]

        if url.startswith("git@"):
            parts = url.split(":")
            if len(parts) == 2:
                return parts[-1]

        name = url.split("/")[-1]

        return name


def create_repo_manager(repos_dir: str = DEFAULT_REPOS_DIR) -> RepositoryManager:
    """Create a repository manager.

    Args:
        repos_dir: Directory to store repositories

    Returns:
        RepositoryManager instance
    """
    return RepositoryManager(repos_dir)
