"""
Configuration Service

Centralized configuration management for the SigmaHQ RAG application.
Handles loading, saving, and updating configuration from a single source of truth.
"""

import asyncio
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RepositoryConfig:
    """Configuration for a single repository."""

    url: str
    branch: str
    enabled: bool
    file_extensions: list[str]


@dataclass
class LLMConfig:
    """Configuration for LLM settings."""

    model: str
    temperature: float
    max_tokens: int
    base_url: str


@dataclass
class AppConfig:
    """Complete application configuration."""

    repositories: list[RepositoryConfig]
    llm: LLMConfig
    rag: dict[str, Any]
    performance: dict[str, Any]


class ConfigService:
    """
    Service for managing application configuration.

    Features:
        - Async configuration loading and saving
        - Configuration validation and defaults
        - Environment variable overrides
        - Configuration caching for performance
        - Thread-safe operations
    """

    def __init__(self, config_path: str = "data/config.json"):
        """
        Initialize the configuration service.

        Args:
            config_path: Path to the configuration file
        """
        self.config_path = Path(config_path)
        self.repositories: list[RepositoryConfig] = []
        self.llm_config: LLMConfig | None = None
        self.app_config: AppConfig | None = None
        self.executor = ThreadPoolExecutor(max_workers=2)

        # Configuration cache
        self._config_cache: dict[str, Any] | None = None
        self._cache_timestamp: float = 0
        self._cache_ttl: int = 30  # 30 seconds cache

        # Load configuration
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from file."""
        if not self.config_path.exists():
            # Create default config if it doesn't exist
            self._create_default_config()
            return

        try:
            with open(self.config_path, encoding="utf-8") as f:
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
            },
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

    def update_repositories(self, repositories: list[RepositoryConfig]) -> bool:
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

    def get_repositories(self) -> list[RepositoryConfig]:
        """
        Get current repository configurations.

        Returns:
            List of repository configurations
        """
        return self.repositories.copy()

    def get_enabled_repositories(self) -> list[RepositoryConfig]:
        """
        Get only enabled repository configurations.

        Returns:
            List of enabled repository configurations
        """
        return [repo for repo in self.repositories if repo.enabled]

    def get_llm_config(self) -> LLMConfig | None:
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
        file_extensions: list[str] | None = None,
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
        file_extensions: list[str] | None = None,
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

    async def load_config_async(self) -> bool:
        """
        Load configuration asynchronously.

        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self.executor, self._load_config)
        except Exception as e:
            logger.error(f"Error loading config asynchronously: {e}")
            return False

    async def save_config_async(self) -> bool:
        """
        Save configuration asynchronously.

        Returns:
            True if successful, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(self.executor, self.save_config)
        except Exception as e:
            logger.error(f"Error saving config asynchronously: {e}")
            return False

    def get_config_with_defaults(self) -> dict[str, Any]:
        """
        Get configuration with environment variable overrides and defaults.

        Returns:
            Complete configuration dictionary
        """
        # Check cache first
        current_time = time.time()
        if (
            self._config_cache
            and (current_time - self._cache_timestamp) < self._cache_ttl
        ):
            return self._config_cache

        # Build configuration with environment overrides
        config = {
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
                "model": os.getenv(
                    "LLM_MODEL",
                    self.llm_config.model if self.llm_config else "llama3.2",
                ),
                "temperature": float(
                    os.getenv(
                        "LLM_TEMPERATURE",
                        self.llm_config.temperature if self.llm_config else 0.7,
                    )
                ),
                "max_tokens": int(
                    os.getenv(
                        "LLM_MAX_TOKENS",
                        self.llm_config.max_tokens if self.llm_config else 1000,
                    )
                ),
                "base_url": os.getenv(
                    "LLM_BASE_URL",
                    (
                        self.llm_config.base_url
                        if self.llm_config
                        else "http://127.0.0.1:1234"
                    ),
                ),
            },
            "rag": {
                "embedding_model": os.getenv(
                    "RAG_EMBEDDING_MODEL", "text-embedding-all-minilm-l6-v2-embedding"
                ),
                "chunk_size": int(os.getenv("RAG_CHUNK_SIZE", "500")),
                "chunk_overlap": int(os.getenv("RAG_CHUNK_OVERLAP", "100")),
                "persist_directory": os.getenv("RAG_PERSIST_DIR", ".chromadb"),
                "cache_size": int(os.getenv("RAG_CACHE_SIZE", "1000")),
                "cache_ttl": int(os.getenv("RAG_CACHE_TTL", "3600")),
            },
            "performance": {
                "max_workers": int(os.getenv("MAX_WORKERS", "4")),
                "thread_pool_size": int(os.getenv("THREAD_POOL_SIZE", "4")),
                "request_timeout": int(os.getenv("REQUEST_TIMEOUT", "30")),
            },
        }

        # Cache the result
        self._config_cache = config
        self._cache_timestamp = current_time

        return config

    def validate_config(self) -> list[str]:
        """
        Validate the current configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Validate LLM config
        if self.llm_config:
            if not self.llm_config.model:
                errors.append("LLM model name is required")
            if not self.llm_config.base_url:
                errors.append("LLM base URL is required")
            if not (0.0 <= self.llm_config.temperature <= 1.0):
                errors.append("LLM temperature must be between 0.0 and 1.0")
            if not (1 <= self.llm_config.max_tokens <= 8192):
                errors.append("LLM max_tokens must be between 1 and 8192")

        # Validate repositories
        for i, repo in enumerate(self.repositories):
            if not repo.url:
                errors.append(f"Repository {i+1} URL is required")
            if not repo.branch:
                errors.append(f"Repository {i+1} branch is required")

        return errors

    def reset_to_defaults(self) -> bool:
        """
        Reset configuration to default values.

        Returns:
            True if successful, False otherwise
        """
        try:
            self._create_default_config()
            return True
        except Exception as e:
            logger.error(f"Error resetting to defaults: {e}")
            return False

    def export_config(self) -> dict[str, Any]:
        """
        Export complete configuration for backup or sharing.

        Returns:
            Complete configuration with metadata
        """
        return {
            "config": self.get_config_with_defaults(),
            "metadata": {
                "exported_at": time.time(),
                "version": "1.0.0",
                "repository_count": len(self.repositories),
                "enabled_count": self.get_enabled_count(),
            },
        }

    def import_config(self, config_data: dict[str, Any]) -> bool:
        """
        Import configuration from exported data.

        Args:
            config_data: Configuration data to import

        Returns:
            True if successful, False otherwise
        """
        try:
            if "config" not in config_data:
                raise ValueError("Invalid configuration format")

            config = config_data["config"]

            # Update repositories
            if "repositories" in config:
                self.repositories = [
                    RepositoryConfig(
                        url=repo["url"],
                        branch=repo["branch"],
                        enabled=repo.get("enabled", True),
                        file_extensions=repo.get("file_extensions", []),
                    )
                    for repo in config["repositories"]
                ]

            # Update LLM config
            if "llm" in config:
                llm_data = config["llm"]
                self.llm_config = LLMConfig(
                    model=llm_data.get("model", "llama3.2"),
                    temperature=llm_data.get("temperature", 0.7),
                    max_tokens=llm_data.get("max_tokens", 1000),
                    base_url=llm_data.get("base_url", "http://127.0.0.1:1234"),
                )

            # Clear cache since config changed
            self._config_cache = None

            return self.save_config()

        except Exception as e:
            logger.error(f"Error importing configuration: {e}")
            return False

    def cleanup(self):
        """Clean up resources."""
        try:
            self.executor.shutdown(wait=True)
        except Exception as e:
            logger.error(f"Error during config service cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()
