"""Git repository management."""

from __future__ import annotations

import json
import logging
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Any

from git import Repo

logger = logging.getLogger(__name__)

DEFAULT_REPOS_DIR = "data/repos"
LOCKFILE = ".cloning"
METADATA_FILE = "metadata.json"


class RepositoryManager:
    """Manage Git repositories."""

    def __init__(self, repos_dir: str = DEFAULT_REPOS_DIR) -> None:
        """Initialize repository manager.

        Args:
            repos_dir: Base directory to store repositories
        """
        self.repos_dir = Path(repos_dir).resolve()
        self.repos_dir.mkdir(parents=True, exist_ok=True)

    def _get_repo_path(self, org: str, name: str) -> Path:
        """Get the full path for a repository.

        Args:
            org: Organization name
            name: Repository name

        Returns:
            Full path to the repository
        """
        return self.repos_dir / org / name

    def clone(
        self,
        url: str | None = None,
        org: str | None = None,
        name: str | None = None,
        progress: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        """Clone a Git repository.

        Args:
            url: Git repository URL (optional, will be constructed from org/name if not provided)
            org: Organization name (used in path structure, required if url not provided)
            name: Repository name (defaults to repo name from url or org/name)
            progress: Optional callback for progress updates

        Returns:
            Dict with clone status and info
        """
        # Construct URL if not provided
        if url is None:
            if not org or not name:
                return {
                    "success": False,
                    "error": "org and name required when url is not provided",
                }
            url = f"https://github.com/{org}/{name}.git"

        if name is None:
            name = self._extract_repo_name(url)

        # Ensure org is set for path construction
        if org is None:
            # Try to extract org from URL
            parts = url.rstrip("/").split("/")
            if len(parts) >= 2:
                org = parts[-2]

        if org is None:
            return {
                "success": False,
                "error": "Could not determine organization",
            }

        dest_path = self._get_repo_path(org, name)

        if dest_path.exists():
            if not self._is_valid_repo(dest_path):
                shutil.rmtree(dest_path, ignore_errors=True)
            else:
                return {
                    "success": False,
                    "error": f"Repository '{org}/{name}' already exists",
                }

        lockfile = dest_path / LOCKFILE
        if lockfile.exists():
            return {
                "success": False,
                "error": f"Repository '{org}/{name}' is currently being cloned",
            }

        try:
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            Repo.clone_from(url, dest_path)
            logger.info(f"Cloned repository: {url} -> {dest_path}")

            return {
                "success": True,
                "org": org,
                "name": name,
                "path": str(dest_path),
            }
        except Exception as e:
            logger.error(f"Failed to clone {url}: {e}")
            if dest_path.exists():
                shutil.rmtree(dest_path, ignore_errors=True)
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
        for org_dir in self.repos_dir.iterdir():
            if not org_dir.is_dir():
                continue
            for repo_dir in org_dir.iterdir():
                if repo_dir.is_dir() and self._is_valid_repo(repo_dir):
                    repos.append(
                        {
                            "org": org_dir.name,
                            "name": repo_dir.name,
                            "path": str(repo_dir),
                        }
                    )
        return sorted(repos, key=lambda r: (r["org"], r["name"]))

    def delete(self, org: str, name: str) -> dict[str, Any]:
        """Delete a repository.

        Args:
            org: Organization name
            name: Repository name

        Returns:
            Dict with delete status
        """
        repo_path = self._get_repo_path(org, name)

        if not repo_path.exists():
            return {
                "success": False,
                "error": f"Repository '{org}/{name}' not found",
            }

        try:
            shutil.rmtree(repo_path)
            logger.info(f"Deleted repository: {org}/{name}")
            # Remove org directory if empty
            try:
                org_path = self.repos_dir / org
                if not any(org_path.iterdir()):
                    org_path.rmdir()
            except Exception:
                pass
            return {
                "success": True,
            }
        except Exception as e:
            logger.error(f"Failed to delete {org}/{name}: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def get_repo_path(self, org: str, name: str) -> Path | None:
        """Get path to a repository.

        Args:
            org: Organization name
            name: Repository name

        Returns:
            Path to repository or None if not found
        """
        repo_path = self._get_repo_path(org, name)
        if repo_path.exists() and (repo_path / ".git").exists():
            return repo_path
        return None

    def update(self, org: str, name: str, branch: str = "main") -> dict[str, Any]:
        """Update a Git repository by pulling latest changes.

        Args:
            org: Organization name
            name: Repository name
            branch: Branch to pull from

        Returns:
            Dict with update status and info
        """
        repo_path = self._get_repo_path(org, name)

        if not repo_path.exists():
            return {
                "success": False,
                "error": f"Repository '{org}/{name}' not found",
            }

        try:
            repo = Repo(repo_path)
            origin = repo.remotes.origin
            origin.pull(branch)
            logger.info(f"Updated repository: {org}/{name} on branch {branch}")

            return {
                "success": True,
                "org": org,
                "name": name,
                "path": str(repo_path),
                "branch": branch,
            }
        except Exception as e:
            logger.error(f"Failed to update {org}/{name}: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def save_metadata(self, org: str, name: str, metadata: dict[str, Any]) -> None:
        """Save metadata for a repository.

        Args:
            org: Organization name
            name: Repository name
            metadata: Metadata dict to save
        """
        repo_path = self._get_repo_path(org, name)
        if not repo_path.exists():
            logger.error(f"Repository '{org}/{name}' not found, cannot save metadata")
            return

        metadata_path = repo_path / METADATA_FILE

        try:
            with open(metadata_path, "w") as f:
                json.dump(metadata, f, indent=2)
        except TypeError as e:
            logger.error(f"Failed to serialize metadata for '{org}/{name}': {e}")
            return

        logger.info(f"Saved metadata for repository: {org}/{name}")

    def get_metadata(self, org: str, name: str) -> dict[str, Any] | None:
        """Get metadata for a repository.

        Args:
            org: Organization name
            name: Repository name

        Returns:
            Metadata dict or None if not found or invalid
        """
        repo_path = self._get_repo_path(org, name)
        metadata_path = repo_path / METADATA_FILE

        if not metadata_path.exists():
            return None

        try:
            with open(metadata_path) as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse metadata for '{org}/{name}': {e}")
            return None

    def list_with_metadata(self) -> list[dict[str, Any]]:
        """List all repositories with their metadata.

        Returns:
            List of repository info dicts with metadata
        """
        repos = []
        for org_dir in self.repos_dir.iterdir():
            if not org_dir.is_dir():
                continue
            for repo_dir in org_dir.iterdir():
                if repo_dir.is_dir() and self._is_valid_repo(repo_dir):
                    repo_info = {
                        "org": org_dir.name,
                        "name": repo_dir.name,
                        "path": str(repo_dir),
                    }
                    metadata = self.get_metadata(org_dir.name, repo_dir.name)
                    if metadata:
                        repo_info["metadata"] = metadata
                    repos.append(repo_info)
        return sorted(repos, key=lambda r: (r["org"], r["name"]))

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
