"""
Data Service for SigmaHQ RAG application.

Provides data management operations including database statistics,
repository cloning, indexing, and context management.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from src.shared.utils import retry_with_backoff
from src.models.logging_service import get_logger

logger = get_logger(__name__)


class DataService:
    """
    Service for managing data operations in the RAG application.

    Features:
    - Context management (clear, store)
    - Repository operations (clone, index)
    - Statistics retrieval
    - Config service integration
    """

    def __init__(self):
        """Initialize the data service."""
        self.config_service = None  # Will be set by external services
        self._initialized = False

    async def initialize(self):
        """Initialize the data service."""
        if not self._initialized:
            logger.info("Initializing Data Service")
            self._initialized = True

    def cleanup(self):
        """Clean up resources."""
        self._initialized = False
        logger.info("Data Service cleaned up")

    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    async def get_context_stats(self) -> dict[str, Any]:
        """
        Get statistics about the stored context from RAG service.

        Returns:
            Dictionary with context statistics
        """
        stats = {
            "count": 0,
            "size_mb": 0,
            "embedding_model": "Unknown",
            "default_chunk_size": "Unknown",
            "default_chunk_overlap": "Unknown",
            "status": "Initializing...",
            "timestamp": datetime.now().isoformat(),
        }

        # Check if RAG persistence directory exists
        try:
            from src.core.rag_service import DEFAULT_RAG_PERSIST_DIRECTORY

            rag_dir = Path(DEFAULT_RAG_PERSIST_DIRECTORY)

            if rag_dir.exists():
                stats["count"] = self._count_documents_in_directory(rag_dir)
                stats["size_mb"] = round(rag_dir.stat().st_size / (1024 * 1024), 2)
                stats["status"] = "Active"

            # Get config file info if exists
            config_file = rag_dir / "config.json"
            if config_file.exists():
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        config_data = json.load(f)
                        if "embeddings_model_name" in config_data:
                            stats["embedding_model"] = config_data[
                                "embeddings_model_name"
                            ]
                        if "chunk_size" in config_data:
                            stats["default_chunk_size"] = config_data["chunk_size"]
                        if "chunk_overlap" in config_data:
                            stats["default_chunk_overlap"] = config_data[
                                "chunk_overlap"
                            ]

                except Exception as e:
                    logger.warning(f"Error reading config file: {e}")

        except Exception as e:
            logger.error(f"Error getting context stats: {e}")
            stats["error"] = str(e)

        return stats

    @staticmethod
    def _count_documents_in_directory(directory: Path) -> int:
        """Count documents in a directory."""
        count = 0
        for file_path in directory.iterdir():
            if file_path.is_file() and not file_path.name.startswith("."):
                # Simple heuristic: count JSON files as potential chunks
                if file_path.suffix == ".json":
                    count += 1
        return count

    @retry_with_backoff(max_retries=2, base_delay=0.5, max_delay=5.0)
    async def clone_enabled_repositories(
        self, repo_config: dict[str, Any]
    ) -> bool:
        """
        Clone enabled repositories to the data directory.

        Args:
            repo_config: Dictionary with repository configuration

        Returns:
            True if cloning was successful
        """
        from src.components.github_management import GitHubConfigManager

        try:
            logger.info("Starting repository cloning...")

            config_manager = GitHubConfigManager()

            for repo in repo_config.get("repositories", []):
                if not repo.get("enabled", False):
                    continue

                url = repo.get("url", "")
                branch = repo.get("branch", "main")

                logger.info(f"Cloning repository: {url} (branch: {branch})")

                # Clone the repository using GitHub manager
                success = config_manager.clone_repository(url, branch)

                if not success:
                    logger.error(f"Failed to clone repository: {url}")
                    return False

            logger.info("All repositories cloned successfully")
            return True

        except Exception as e:
            logger.error(f"Error cloning repositories: {e}")
            return False

    @retry_with_backoff(max_retries=2, base_delay=0.5, max_delay=5.0)
    async def index_enabled_repositories(
        self, repo_config: dict[str, Any]
    ) -> bool:
        """
        Index content from enabled repositories into RAG.

        Args:
            repo_config: Dictionary with repository configuration

        Returns:
            True if indexing was successful
        """
        from src.components.github_management import GitHubConfigManager
        from src.core.rag_service import DEFAULT_RAG_PERSIST_DIRECTORY

        try:
            logger.info("Starting repository indexing...")

            rag_dir = Path(DEFAULT_RAG_PERSIST_DIRECTORY)
            config_manager = GitHubConfigManager()

            for repo in repo_config.get("repositories", []):
                if not repo.get("enabled", False):
                    continue

                url = repo.get("url", "")
                branch = repo.get("branch", "main")

                logger.info(f"Indexing repository: {url} (branch: {branch})")

                # Get repository content using GitHub manager
                content_path = config_manager.get_repository_content(url, branch)

                if not content_path or not content_path.exists():
                    logger.warning(f"No content found for repository: {url}")
                    continue

                # Index the content into RAG
                success = self._index_directory(content_path, url)

                if not success:
                    logger.error(f"Failed to index repository: {url}")
                    return False

            logger.info("All repositories indexed successfully")
            return True

        except Exception as e:
            logger.error(f"Error indexing repositories: {e}")
            return False

    def _index_directory(self, directory: Path, source_url: str) -> bool:
        """
        Index a directory of content into RAG.

        Args:
            directory: Path to the directory to index
            source_url: URL of the source (for metadata)

        Returns:
            True if indexing was successful
        """
        try:
            from src.core.rag_service import RAGService, create_rag_service
            from src.core.llm_service import LLMService
            from src.models.config_service import ConfigService
            from src.application.app_factory import Application

            # Check if service is already initialized
            if self.config_service is None:
                self.config_service = ConfigService()

            app_state = self.config_service.get_app_state()

            if app_state and "services" in app_state and "llm_service" in app_state[
                "services"
            ]:
                llm_service = app_state["services"]["llm_service"]
            else:
                logger.info("No LLM service available, skipping indexing")
                return True

            # Create RAG service
            rag_service = create_rag_service(llm_service=llm_service)

            # Initialize if needed
            asyncio.create_task(rag_service.initialize())

            # Index files from the directory
            for file_path in directory.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in [
                    ".md",
                    ".txt",
                    ".json",
                ]:
                    try:
                        # Read file content
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()

                        # Create document ID from path
                        doc_id = source_url + "/" + file_path.name

                        # Store in RAG (async)
                        def store_in_rag_sync():
                            return asyncio.run(
                                rag_service.store_context(
                                    document_id=doc_id, text_content=content, metadata={}
                                )
                            )

                        asyncio.create_task(store_in_rag_sync())

                    except Exception as e:
                        logger.error(f"Error indexing file {file_path}: {e}")

            logger.info(f"Indexed content from {directory}")
            return True

        except Exception as e:
            logger.error(f"Error in directory indexing: {e}")
            return False

    async def clear_context(self) -> bool:
        """
        Clear all stored context from RAG.

        Returns:
            True if clearing was successful
        """
        try:
            from src.core.rag_service import create_rag_service
            from src.core.llm_service import LLMService
            from src.models.config_service import ConfigService
            from src.application.app_factory import Application

            # Check if service is already initialized
            if self.config_service is None:
                self.config_service = ConfigService()

            app_state = self.config_service.get_app_state()

            if app_state and "services" in app_state and "llm_service" in app_state[
                "services"
            ]:
                llm_service = app_state["services"]["llm_service"]
            else:
                logger.info("No LLM service available, skipping context clear")
                return True

            # Create RAG service
            rag_service = create_rag_service(llm_service=llm_service)

            # Initialize if needed
            asyncio.create_task(rag_service.initialize())

            # Clear context
            success = await rag_service.clear_context()

            if success:
                logger.info("Context cleared successfully")

            return success

        except Exception as e:
            logger.error(f"Error clearing context: {e}")
            return False

    @retry_with_backoff(max_retries=2, base_delay=0.5, max_delay=5.0)
    async def sync_database(self) -> bool:
        """
        Sync database with repository content.

        Returns:
            True if sync was successful
        """
        try:
            logger.info("Syncing database...")
            return await self.index_enabled_repositories(
                {"repositories": []}  # Empty config - just test connection
            )
        except Exception as e:
            logger.error(f"Error syncing database: {e}")
            return False

    def get_database_health(self) -> dict[str, Any]:
        """
        Get health status of the data service and RAG.

        Returns:
            Dictionary with health information
        """
        health = {
            "initialized": self._initialized,
            "status": "healthy",
            "message": "Ready",
        }

        if not self._initialized:
            health["status"] = "initializing"
            health["message"] = "Service is initializing..."

        return health