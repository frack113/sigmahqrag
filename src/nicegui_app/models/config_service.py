"""
Configuration Service

Centralized configuration management for the SigmaHQ RAG application.
Handles loading, saving, and updating configuration from a single source of truth.
"""

import json
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class RepositoryConfig:
    """Configuration for a single repository."""
    url: str
    branch: str
    enabled: bool
    file_extensions: List[str]


@dataclass
class LLMConfig:
    """Configuration for LLM settings."""
    model: str
    temperature: float
    max_tokens: int
    base_url: str


class ConfigService:
    """
    Service for managing application configuration.

    Attributes:
        config_path: Path to the configuration file
        repositories: List of repository configurations
        llm_config: LLM configuration
    """

    def __init__(self, config_path: str = "data/config.json"):
        """
        Initialize the configuration service.

        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        self.repositories: List[RepositoryConfig] = []
        self.llm_config: Optional[LLMConfig] = None
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        if not self.config_path.exists():
            # Create default config if it doesn't exist
            self._create_default_config()
            return

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            # Load repositories
            if "repositories" in config_data:
                self.repositories = [
                    RepositoryConfig(
                        url=repo["url"],
                        branch=repo["branch"],
                        enabled=repo.get("enabled", True),
                        file_extensions=repo.get("file_extensions", []),
                    )
                    for repo in config_data["repositories"]
                ]

            # Load LLM config
            if "llm" in config_data:
                llm_data = config_data["llm"]
                self.llm_config = LLMConfig(
                    model=llm_data.get("model", "llama3.2"),
                    temperature=llm_data.get("temperature", 0.7),
                    max_tokens=llm_data.get("max_tokens", 1000),
                    base_url=llm_data.get("base_url", "http://127.0.0.1:1234"),
                )

        except Exception as e:
            print(f"Error loading configuration: {e}")
            self._create_default_config()

    def _create_default_config(self) -> None:
        """Create default configuration file."""
        default_config = {
            "repositories": [],
            "llm": {
                "model": "llama3.2",
                "temperature": 0.7,
                "max_tokens": 1000,
                "base_url": "http://127.0.0.1:1234",
            }
        }

        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=2)

        self.repositories = []
        self.llm_config = LLMConfig(
            model="llama3.2",
            temperature=0.7,
            max_tokens=1000,
            base_url="http://127.0.0.1:1234",
        )

    def save_config(self) -> bool:
        """
        Save current configuration to file.

        Returns:
            True if successful, False otherwise
        """
        try:
            config_data = {
                "repositories": [
                    {
                        "url": repo.url,
                        "branch": repo.branch,
                        "enabled": repo.enabled,
                        "file_extensions": repo.file_extensions,
                    }
                    for repo in self.repositories
                ],
                "llm": {
                    "model": self.llm_config.model,
                    "temperature": self.llm_config.temperature,
                    "max_tokens": self.llm_config.max_tokens,
                    "base_url": self.llm_config.base_url,
                },
            }

            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2)

            return True

        except Exception as e:
            print(f"Error saving configuration: {e}")
            return False

    def update_repositories(self, repositories: List[RepositoryConfig]) -> bool:
        """
        Update repository configurations.

        Args:
            repositories: New list of repository configurations

        Returns:
            True if successful, False otherwise
        """
        try:
            self.repositories = repositories
            return self.save_config()

        except Exception as e:
            print(f"Error updating repositories: {e}")
            return False

    def update_llm_config(self, llm_config: LLMConfig) -> bool:
        """
        Update LLM configuration.

        Args:
            llm_config: New LLM configuration

        Returns:
            True if successful, False otherwise
        """
        try:
            self.llm_config = llm_config
            return self.save_config()

        except Exception as e:
            print(f"Error updating LLM config: {e}")
            return False

    def get_repositories(self) -> List[RepositoryConfig]:
        """
        Get current repository configurations.

        Returns:
            List of repository configurations
        """
        return self.repositories.copy()

    def get_enabled_repositories(self) -> List[RepositoryConfig]:
        """
        Get only enabled repository configurations.

        Returns:
            List of enabled repository configurations
        """
        return [repo for repo in self.repositories if repo.enabled]

    def get_llm_config(self) -> Optional[LLMConfig]:
        """
        Get current LLM configuration.

        Returns:
            LLM configuration or None
        """
        return self.llm_config

    def add_repository(
        self,
        url: str,
        branch: str,
        enabled: bool = True,
        file_extensions: Optional[List[str]] = None,
    ) -> bool:
        """
        Add a new repository configuration.

        Args:
            url: Repository URL
            branch: Branch name
            enabled: Whether repository is enabled
            file_extensions: List of file extensions to index

        Returns:
            True if successful, False otherwise
        """
        try:
            new_repo = RepositoryConfig(
                url=url,
                branch=branch,
                enabled=enabled,
                file_extensions=file_extensions or [],
            )
            self.repositories.append(new_repo)
            return self.save_config()

        except Exception as e:
            print(f"Error adding repository: {e}")
            return False

    def remove_repository(self, index: int) -> bool:
        """
        Remove a repository by index.

        Args:
            index: Index of repository to remove

        Returns:
            True if successful, False otherwise
        """
        try:
            if 0 <= index < len(self.repositories):
                self.repositories.pop(index)
                return self.save_config()
            return False

        except Exception as e:
            print(f"Error removing repository: {e}")
            return False

    def update_repository(
        self,
        index: int,
        url: str,
        branch: str,
        enabled: bool,
        file_extensions: Optional[List[str]] = None,
    ) -> bool:
        """
        Update an existing repository configuration.

        Args:
            index: Index of repository to update
            url: New repository URL
            branch: New branch name
            enabled: New enabled status
            file_extensions: New list of file extensions

        Returns:
            True if successful, False otherwise
        """
        try:
            if 0 <= index < len(self.repositories):
                self.repositories[index] = RepositoryConfig(
                    url=url,
                    branch=branch,
                    enabled=enabled,
                    file_extensions=file_extensions or [],
                )
                return self.save_config()
            return False

        except Exception as e:
            print(f"Error updating repository: {e}")
            return False

    def get_repository_count(self) -> int:
        """
        Get the total number of repositories.

        Returns:
            Number of repositories
        """
        return len(self.repositories)

    def get_enabled_count(self) -> int:
        """
        Get the number of enabled repositories.

        Returns:
            Number of enabled repositories
        """
        return sum(1 for repo in self.repositories if repo.enabled)