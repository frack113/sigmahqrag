# Repository Service for Gradio - GitHub repository management
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import requests
from git import Repo


class RepositoryService:
    """
    An optimized service to handle GitHub repository operations.

    Features:
        - Concurrent repository cloning and updating
        - Async operations for better performance
        - Thread pool execution for CPU-bound operations
        - Comprehensive error handling and logging
        - Progress tracking and status reporting
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize the repository service.

        Args:
            max_workers: Maximum number of worker threads for concurrent operations
        """
        self.logger = logging.getLogger(__name__)
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Import GitPython for repository operations
        try:
            import git  # noqa: F401

            self.GITPYTHON_AVAILABLE = True
        except ImportError as e:
            self.logger.warning(f"GitPython not available: {e}")
            self.GITPYTHON_AVAILABLE = False

    async def fetch_github_repositories(
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
        if not self.GITPYTHON_AVAILABLE:
            self.logger.error("GitPython not available")
            return []

        repositories = []

        try:
            # Process repositories concurrently
            tasks = []
            for repo in repo_config.get("repositories", []):
                task = self._fetch_single_repository(repo)
                tasks.append(task)

            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)

                for result in results:
                    if isinstance(result, Exception):
                        self.logger.error(f"Failed to fetch repository: {result}")
                    elif result:
                        repositories.append(result)

        except Exception as e:
            self.logger.error(f"Error fetching GitHub repositories: {e}")

        return repositories

    async def _fetch_single_repository(
        self, repo: dict[str, Any]
    ) -> dict[str, Any] | None:
        """Fetch a single repository asynchronously."""
        try:
            url = repo.get("url")
            branch = repo.get("branch", "main")
            enabled = repo.get("enabled", True)
            file_extensions = repo.get("file_extensions", [])

            if not url:
                return None

            # Extract owner and repo name from URL
            parts = url.strip().split("/")
            if len(parts) < 5 or parts[2] != "github.com":
                self.logger.warning(f"Invalid GitHub repository URL: {url}")
                return None

            owner, repo_name = parts[3], parts[4]
            api_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents?path=/&ref={branch}"

            # Fetch repository contents from GitHub API with rate limit handling
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(self.executor, requests.get, api_url)

            # Handle rate limiting
            if response.status_code == 403:
                self.logger.warning(
                    "GitHub API rate limit exceeded. Please wait before retrying."
                )
                return None

            if response.status_code == 200:
                contents = response.json()
                return {
                    "url": url,
                    "branch": branch,
                    "contents": contents,
                    "enabled": enabled,
                    "file_extensions": file_extensions,
                }
            else:
                self.logger.error(
                    f"Failed to fetch repository {url}: HTTP {response.status_code}"
                )
                return None

        except Exception as e:
            self.logger.error(f"Error fetching repository {url}: {e}")
            return None

    async def clone_enabled_repositories(self, repo_config: dict[str, Any]) -> bool:
        """
        Clone enabled repositories into /data/github and update existing ones.

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
            docs_github_dir = Path("data/github")
            docs_github_dir.mkdir(parents=True, exist_ok=True)

            # Get enabled repositories
            enabled_repos = [
                repo
                for repo in repo_config.get("repositories", [])
                if repo.get("enabled", False)
            ]

            if not enabled_repos:
                self.logger.info("No enabled repositories found")
                return True

            # Process repositories concurrently
            tasks = []
            for repo in enabled_repos:
                task = self._process_single_repository(repo, docs_github_dir)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            success_count = sum(1 for result in results if result is True)
            total_repos = len(enabled_repos)

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

    async def _process_single_repository(
        self, repo: dict[str, Any], docs_github_dir: Path
    ) -> bool:
        """Process a single repository (clone or update)."""
        try:
            url = repo.get("url")
            branch = repo.get("branch", "main")

            if not url:
                self.logger.warning("Repository missing URL, skipping")
                return False

            # Extract owner and repo name from URL
            parts = url.strip().split("/")
            if len(parts) < 5 or parts[2] != "github.com":
                self.logger.warning(f"Invalid GitHub repository URL: {url}")
                return False

            owner, repo_name = parts[3], parts[4]
            repo_dir = docs_github_dir / repo_name

            loop = asyncio.get_event_loop()

            if repo_dir.exists():
                # Update existing repository
                return await loop.run_in_executor(
                    self.executor, self._update_repository, repo_dir, branch
                )
            else:
                # Clone new repository
                clone_url = f"https://github.com/{owner}/{repo_name}.git"
                return await loop.run_in_executor(
                    self.executor, self._clone_repository, clone_url, repo_dir, branch
                )

        except Exception as e:
            self.logger.error(f"Failed to process repository {url}: {e}")
            return False

    def _update_repository(self, repo_dir: Path, branch: str) -> bool:
        """Update an existing repository."""
        try:
            repo_obj = Repo(str(repo_dir))
            origin = repo_obj.remotes.origin
            origin.pull()
            self.logger.info(f"Updated repository: {repo_dir.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update repository {repo_dir.name}: {e}")
            return False

    def _clone_repository(self, clone_url: str, repo_dir: Path, branch: str) -> bool:
        """Clone a new repository."""
        try:
            repo_obj = Repo.clone_from(clone_url, str(repo_dir))
            repo_obj.git.checkout(branch)
            self.logger.info(f"Cloned repository: {repo_dir.name}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to clone repository {repo_dir.name}: {e}")
            return False

    async def index_enabled_repositories(self, repo_config: dict[str, Any]) -> bool:
        """
        Index enabled repositories for RAG operations.

        Args:
            repo_config (Dict[str, Any]): Configuration containing repository URLs
                and branches.

        Returns:
            bool: True if indexing was successful, False otherwise.
        """
        try:
            # Get enabled repositories
            enabled_repos = [
                repo
                for repo in repo_config.get("repositories", [])
                if repo.get("enabled", False)
            ]

            if not enabled_repos:
                self.logger.info("No enabled repositories found for indexing")
                return True

            # Process repositories concurrently
            tasks = []
            for repo in enabled_repos:
                task = self._index_single_repository(repo)
                tasks.append(task)

            results = await asyncio.gather(*tasks, return_exceptions=True)

            success_count = sum(1 for result in results if result is True)
            total_repos = len(enabled_repos)

            if success_count > 0:
                self.logger.info(
                    f"Repository indexing completed. Successfully indexed "
                    f"{success_count}/{total_repos} enabled repositories."
                )
                return True
            else:
                self.logger.warning(
                    "No enabled repositories were successfully indexed."
                )
                return False

        except Exception as e:
            self.logger.error(f"Error indexing repositories: {e}")
            return False

    async def _index_single_repository(self, repo: dict[str, Any]) -> bool:
        """Index a single repository."""
        try:
            url = repo.get("url")
            branch = repo.get("branch", "main")
            file_extensions = repo.get("file_extensions", [])

            if not url:
                return False

            # Extract owner and repo name from URL
            parts = url.strip().split("/")
            if len(parts) < 5 or parts[2] != "github.com":
                return False

            owner, repo_name = parts[3], parts[4]
            repo_dir = Path("data/github") / repo_name

            if not repo_dir.exists():
                self.logger.warning(f"Repository directory not found: {repo_dir}")
                return False

            # Process files in the repository
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                self.executor, self._process_repository_files, repo_dir, file_extensions
            )

        except Exception as e:
            self.logger.error(f"Failed to index repository {url}: {e}")
            return False

    def _process_repository_files(
        self, repo_dir: Path, file_extensions: list[str]
    ) -> bool:
        """Process files in a repository for indexing."""
        try:
            # This would integrate with the RAG service
            # For now, just log the files that would be processed
            processed_count = 0

            for file_path in repo_dir.rglob("*"):
                if file_path.is_file():
                    ext = file_path.suffix.lower()
                    if not file_extensions or ext in file_extensions:
                        # Process file (this would integrate with RAG service)
                        processed_count += 1

            self.logger.info(f"Processed {processed_count} files from {repo_dir.name}")
            return processed_count > 0

        except Exception as e:
            self.logger.error(f"Error processing repository files: {e}")
            return False

    def cleanup(self):
        """Clean up resources."""
        try:
            self.executor.shutdown(wait=True)
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()
