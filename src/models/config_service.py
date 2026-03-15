"""
Configuration Service - Simplified for Gradio Native Integration

Uses data/config.json as the single source of truth.
No fallbacks or DEFAULT_* values - all settings come from config.json.
Requires data/config.json to exist at startup.
"""

import logging
from pathlib import Path
from typing import Any

from src.shared.constants import (
    DATA_GITHUB_PATH,
)

logger = logging.getLogger(__name__)


class RepositoryConfig:
    """Repository configuration data class."""

    def __init__(
        self,
        url: str,
        branch: str,
        enabled: bool = True,
        file_extensions: list[str] | None = None,
    ):
        self.url = url
        self.branch = branch
        self.enabled = enabled
        self.file_extensions = file_extensions or []

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "branch": self.branch,
            "enabled": self.enabled,
            "file_extensions": self.file_extensions,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RepositoryConfig":
        """Create from dictionary."""
        return cls(
            url=data["url"],
            branch=data["branch"],
            enabled=data.get("enabled", True),
            file_extensions=data.get("file_extensions", []),
        )


class ConfigService:
    """
    Configuration service reading directly from data/config.json.

    Features:
    - Single source of truth: data/config.json
    - Repository management via the repositories array in config
    - Uses ConfigManager for configuration access

    Note: All configuration must come from data/config.json.
    Missing required configuration will cause errors at startup.
    """

    def __init__(self, config_path: str | Path | None = None):
        """Initialize with config path (defaults to data/config.json)."""
        from src.shared.config_manager import ConfigManager

        self.config_manager = ConfigManager(
            str(config_path) if config_path else "data/config.json"
        )
        # Initialize and load the config - REQUIRED for _config to be populated
        self.config_manager.initialize()
        self.config_manager.load_config()  # <-- MISSING IN ORIGINAL CODE

    def get_repositories(self) -> list[RepositoryConfig]:
        """Get repository configurations from config.json."""
        repos_data = self.config_manager.get("repositories")

        if not isinstance(repos_data, list):
            return []

        return [
            RepositoryConfig.from_dict(repo)
            for repo in repos_data
            if isinstance(repo, dict)
        ]

    def get_llm_config(self) -> dict[str, Any]:
        """Get LLM configuration from config.json."""
        llm_config = self.config_manager.get("llm")
        return llm_config or {}

    def get_network_config(self) -> dict[str, Any]:
        """Get network configuration from config.json."""
        network_config = self.config_manager.get("network")
        return network_config or {}

    def get_ui_config(self) -> dict[str, Any]:
        """Get UI/CSS configuration from config.json."""
        ui_config = self.config_manager.get("ui_css")
        return ui_config or {}

    def update_repositories(self, repos: list[RepositoryConfig]) -> bool:
        """Update repositories array with new repository configurations.

        Args:
            repos: List of RepositoryConfig objects to save

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current config or use default structure
            repos_data = self.config_manager.get("repositories")

            if not isinstance(repos_data, list):
                repos_data = []

            # Convert RepositoryConfig objects to dicts
            repositories_dict = [repo.to_dict() for repo in repos]

            # Update the repositories array
            self.config_manager.set("repositories", repositories_dict)

            # Save to file synchronously (blocking)
            return self.config_manager.save_config()

        except Exception as e:
            logger.error(f"Error updating repositories: {e}")
            return False

    def clone_enabled_repositories(self, config_data: dict[str, Any]) -> bool:
        """Clone all enabled repositories from config.

        Args:
            config_data: Dictionary containing repositories array

        Returns:
            True if successful, False otherwise
        """
        try:
            repos_list = config_data.get("repositories", [])

            if not repos_list:
                logger.warning("No repositories to clone")
                return True

            import subprocess

            cloned_count = 0
            failed_repos = []

            for repo in repos_list:
                if repo.get("enabled", False):
                    try:
                        url = repo["url"]

                        # Extract repo name from URL (without .git suffix)
                        import urllib.parse

                        parsed_url = urllib.parse.urlparse(url)
                        path_parts = Path(parsed_url.path.lstrip("/")).parts
                        if path_parts and path_parts[-1]:
                            repo_name = path_parts[-1]
                        else:
                            repo_name = "unknown"

                        # Remove .git suffix if present
                        if repo_name.endswith(".git"):
                            repo_name = repo_name[:-4]

                        clone_dir = Path(DATA_GITHUB_PATH) / repo_name

                        # Check if already cloned (case-insensitive check for Windows)
                        if clone_dir.exists() or (
                            clone_dir.parent.exists()
                            and any(
                                clone_dir.name.lower() in f.name.lower()
                                for f in clone_dir.parent.iterdir()
                            )
                        ):
                            logger.info(f"Skipping already cloned repo: {url}")
                            continue

                        branch_name = repo.get("branch", "main").replace(" ", "_")

                        result = subprocess.run(
                            [
                                "git",
                                "clone",
                                "--depth=1",
                                url,
                                str(clone_dir / branch_name),
                            ],
                            capture_output=True,
                            text=True,
                            timeout=300,  # 5 minutes per repo
                        )

                        if result.returncode == 0:
                            logger.info(f"Successfully cloned: {url} -> {clone_dir}")
                            cloned_count += 1
                        else:
                            failed_repos.append(
                                {
                                    "url": url,
                                    "error": result.stderr[
                                        :200
                                    ],  # Truncate long errors
                                }
                            )
                            logger.error(
                                f"Failed to clone {url}: {result.stderr[:200]}"
                            )

                    except subprocess.TimeoutExpired:
                        failed_repos.append(
                            {"url": repo.get("url", "unknown"), "error": "timeout"}
                        )
                        logger.error(f"Clone timeout for: {repo.get('url')}")
                    except Exception as e:
                        failed_repos.append(
                            {"url": repo.get("url", "unknown"), "error": str(e)}
                        )
                        logger.error(f"Failed to clone {repo.get('url')}: {e}")

            success = cloned_count > 0 or not failed_repos
            if not success and failed_repos:
                logger.warning(
                    f"Some repos failed to clone: {[r['url'] for r in failed_repos]}"
                )

            return success

        except Exception as e:
            logger.error(f"Error cloning repositories: {e}")
            return False

    def cleanup(self):
        """Clean up resources."""
        pass
