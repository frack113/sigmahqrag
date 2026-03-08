# Repository Service for NiceGUI - GitHub repository management
import logging
from pathlib import Path
from typing import Any


class RepositoryService:
    """
    A service to handle GitHub repository operations.

    Methods:
        - fetch_github_repositories: Fetch repositories from GitHub API
        - clone_enabled_repositories: Clone or update enabled repositories
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # Import GitPython for repository operations
        try:
            import git  # noqa: F401

            self.GITPYTHON_AVAILABLE = True
        except ImportError as e:
            self.logger.warning(f"GitPython not available: {e}")
            self.GITPYTHON_AVAILABLE = False

    def fetch_github_repositories(
        self, repo_config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """
        Fetch GitHub repositories based on the provided configuration.

        Args:
            repo_config (Dict[str, Any]): Configuration containing repository URLs
                and branches.

        Returns:
            List[Dict[str, Any]]: List of fetched repositories with metadata.
        """
        try:
            import requests
        except ImportError as e:
            self.logger.error(f"requests library not available: {e}")
            return []

        repositories = []

        try:
            for repo in repo_config.get("repositories", []):
                url = repo.get("url")
                branch = repo.get("branch", "main")
                enabled = repo.get("enabled", True)
                file_extensions = repo.get("file_extensions", [])

                if not url:
                    continue

                # Extract owner and repo name from URL (e.g., https://github.com/user/repo)
                parts = url.strip().split("/")
                if len(parts) < 5 or parts[2] != "github.com":
                    self.logger.warning(f"Invalid GitHub repository URL: {url}")
                    continue

                owner, repo_name = parts[3], parts[4]
                api_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents?path=/&ref={branch}"

                # Fetch repository contents from GitHub API with rate limit handling
                response = requests.get(api_url)

                # Handle rate limiting
                if response.status_code == 403:
                    self.logger.warning(
                        "GitHub API rate limit exceeded. Please wait before retrying."
                    )
                    return []

                if response.status_code == 200:
                    contents = response.json()
                    repositories.append(
                        {
                            "url": url,
                            "branch": branch,
                            "contents": contents,
                            "enabled": enabled,
                            "file_extensions": file_extensions,
                        }
                    )
                else:
                    self.logger.error(
                        f"Failed to fetch repository {url}: HTTP {response.status_code}"
                    )
        except Exception as e:
            self.logger.error(f"Error fetching GitHub repositories: {e}")

        return repositories

    def clone_enabled_repositories(self, repo_config: dict[str, Any]) -> bool:
        """
        Clone enabled repositories into /docs/github and update existing ones.

        Args:
            repo_config (Dict[str, Any]): Configuration containing repository URLs
                and branches.

        Returns:
            bool: True if cloning was successful, False otherwise.
        """
        if not self.GITPYTHON_AVAILABLE:
            self.logger.error("GitPython not available")
            return False

        try:
            from git import Repo

            docs_github_dir = Path("docs/github")
            docs_github_dir.mkdir(parents=True, exist_ok=True)

            success_count = 0
            total_repos = sum(
                1
                for repo in repo_config.get("repositories", [])
                if repo.get("enabled", False)
            )

            for repo in repo_config.get("repositories", []):
                if not repo.get("enabled", False):
                    continue

                url = repo.get("url")
                branch = repo.get("branch", "main")

                if not url:
                    self.logger.warning("Repository missing URL, skipping")
                    continue

                # Extract owner and repo name from URL (e.g., https://github.com/user/repo)
                parts = url.strip().split("/")
                if len(parts) < 5 or parts[2] != "github.com":
                    self.logger.warning(f"Invalid GitHub repository URL: {url}")
                    continue

                owner, repo_name = parts[3], parts[4]
                repo_dir = docs_github_dir / repo_name

                try:
                    if repo_dir.exists():
                        # Update existing repository using GitPython
                        self.logger.info(f"Updating existing repository: {repo_name}")
                        repo_obj = Repo(str(repo_dir))
                        origin = repo_obj.remotes.origin
                        origin.pull()
                    else:
                        # Clone new repository using GitPython
                        self.logger.info(f"Cloning repository: {repo_name}")
                        repo_obj = Repo.clone_from(
                            f"https://github.com/{owner}/{repo_name}.git", str(repo_dir)
                        )
                        repo_obj.git.checkout(branch)

                    success_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to process repository {repo_name}: {e}")
                    continue

            if success_count > 0:
                self.logger.info(
                    f"Repository update completed. Successfully processed "
                    f"{success_count}/{total_repos} enabled repositories."
                )
                return True
            else:
                self.logger.warning(
                    "No enabled repositories were successfully updated."
                )
                return False
        except Exception as e:
            self.logger.error(f"Error cloning or updating repositories: {e}")
            return False
