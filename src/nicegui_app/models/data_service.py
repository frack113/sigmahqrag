"""
Data Service for NiceGUI - Orchestrates RAG, Repository, and File Processing services
"""

import json
import logging
import os
from typing import Any


class DataService:
    """
    A service to handle data operations by orchestrating specialized sub-services.

    This class acts as a facade that coordinates between:
    - RagService: For embeddings and vector database operations
    - RepositoryService: For GitHub repository management
    - FileProcessor: For processing different file formats

    Methods:
        - get_data: Retrieve data from a source
        - save_data: Save data to a destination
        - index_repository: Index a single repository
        - index_enabled_repositories: Index all enabled repositories from config
    """

    def __init__(self, embedding_model_name: str = "all-MiniLM-L6-v2"):
        self.logger = logging.getLogger(__name__)

        # Initialize sub-services
        from .file_processor import FileProcessor
        from .rag_service import RagService
        from .repository_service import RepositoryService

        self.rag_service = RagService(embedding_model_name=embedding_model_name)
        self.repository_service = RepositoryService()
        self.file_processor = FileProcessor()

    def get_data(self, key: str) -> dict[str, Any] | None:
        """
        Retrieve data for the given key.

        Args:
            key (str): The key to retrieve data for.

        Returns:
            Optional[Dict[str, Any]]: The retrieved data or None if not found.
        """
        # TODO: Implement actual data retrieval logic
        # This could involve database queries, file reads, or API calls
        self.logger.info(f"Retrieving data for key: {key}")
        return None

    def save_data(self, key: str, data: dict[str, Any]) -> bool:
        """
        Save the given data for the specified key.

        Args:
            key (str): The key to save data under.
            data (Dict[str, Any]): The data to save.

        Returns:
            bool: True if data was saved successfully, False otherwise.
        """
        # TODO: Implement actual data persistence logic
        # This could involve database writes, file saves, or API calls
        self.logger.info(f"Saving data for key: {key}")
        return True

    def index_repository(self, repo_config: dict[str, Any]) -> bool:
        """
        Index a repository by processing files based on allowed extensions.

        Args:
            repo_config (Dict[str, Any]): Configuration for the repository

        Returns:
            bool: True if indexing was successful, False otherwise
        """
        try:
            url = repo_config.get("url")
            branch = repo_config.get("branch", "main")
            file_extensions = repo_config.get("file_extensions", [])

            if not url or not file_extensions:
                self.logger.warning(
                    f"Repository {url} missing URL or file extensions. Skipping."
                )
                return False

            # Extract repository name from URL
            parts = url.strip().split("/")
            if len(parts) < 5 or parts[2] != "github.com":
                self.logger.warning(f"Invalid GitHub repository URL: {url}")
                return False

            repo_name = parts[4]
            repo_dir = os.path.join("data", "github", repo_name)

            if not os.path.exists(repo_dir):
                self.logger.warning(
                    f"Repository directory not found: {repo_dir}. "
                    "Clone the repository first."
                )
                return False

            # Traverse the repository and process files
            processed_count = 0
            total_files = 0
            
            # First, count total files to process
            for root, _, files in os.walk(repo_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext in file_extensions:
                        total_files += 1

            self.logger.info(f"Found {total_files} files to process in repository {repo_name}")

            for root, _, files in os.walk(repo_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = os.path.splitext(file)[1].lower()

                    # Check if file extension is allowed
                    if file_ext not in file_extensions:
                        continue

                    try:
                        # Show progress notification for each file
                        relative_path = os.path.relpath(file_path, repo_dir)
                        self.logger.info(f"Processing file: {relative_path}")
                        
                        # Process the file using FileProcessor
                        content = self.file_processor.process_file(file_path)
                        if content:
                            # Create a unique document ID
                            doc_id = self.file_processor.create_document_id(file_path)

                            # Prepare metadata
                            metadata = self.file_processor.create_metadata(
                                file_path=file_path,
                                repo_name=repo_name,
                                branch=branch,
                                repo_dir=repo_dir,
                            )

                            # Store the context using RagService
                            self.rag_service.store_context(doc_id, content, metadata)
                            processed_count += 1
                            
                            # Log progress
                            self.logger.info(
                                f"Successfully processed: {relative_path} "
                                f"({processed_count}/{total_files})"
                            )
                    except Exception as e:
                        self.logger.error(f"Error processing file {file_path}: {e}")
                        continue

            self.logger.info(
                f"Indexed {processed_count} files from repository {repo_name}"
            )
            return True
        except Exception as e:
            self.logger.error(f"Error indexing repository: {e}")
            return False

    def index_enabled_repositories(self, repo_config: dict[str, Any]) -> bool:
        """
        Index all enabled repositories from the configuration.

        Args:
            repo_config (Dict[str, Any]): Repository configuration dictionary

        Returns:
            bool: True if indexing was successful for at least one repository,
                 False otherwise
        """
        try:
            repositories = repo_config.get("repositories", [])
            if not repositories:
                self.logger.warning("No repositories found in configuration.")
                return False

            success_count = 0
            total_repos = len(repositories)

            for repo in repositories:
                if repo.get("enabled", True):
                    try:
                        if self.index_repository(repo):
                            success_count += 1
                    except Exception as e:
                        self.logger.error(
                            f"Error indexing repository {repo.get('url')}: {e}"
                        )
                        continue

            if success_count > 0:
                self.logger.info(
                    f"Indexing completed. "
                    f"Successfully indexed {success_count}/{total_repos} "
                    f"enabled repositories."
                )
                return True
            else:
                self.logger.warning(
                    "No enabled repositories were successfully indexed."
                )
                return False
        except Exception as e:
            self.logger.error(f"Error indexing enabled repositories: {e}")
            return False

    # --- Delegated methods for backward compatibility ---

    def fetch_github_repositories(
        self, repo_config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Delegate to RepositoryService."""
        return self.repository_service.fetch_github_repositories(repo_config)

    def clone_enabled_repositories(self, repo_config: dict[str, Any]) -> bool:
        """Delegate to RepositoryService."""
        return self.repository_service.clone_enabled_repositories(repo_config)

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Delegate to RagService."""
        return self.rag_service.generate_embeddings(texts)

    def store_context(
        self,
        document_id: str,
        text_content: str,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """Delegate to RagService."""
        return self.rag_service.store_context(document_id, text_content, metadata)

    def retrieve_context(
        self, query: str, n_results: int = 5, min_relevance_score: float = 0.3
    ) -> tuple[list[str], list[dict[str, Any]]]:
        """Delegate to RagService."""
        return self.rag_service.retrieve_context(query, n_results, min_relevance_score)

    def clear_context(self) -> bool:
        """Delegate to RagService."""
        return self.rag_service.clear_context()

    def get_context_stats(self) -> dict[str, Any]:
        """Delegate to RagService."""
        return self.rag_service.get_context_stats()

    def check_ollama_model(self, model_name: str) -> bool:
        """Delegate to RagService."""
        return self.rag_service.check_ollama_model(model_name)

    def pull_ollama_model(self, model_name: str) -> bool:
        """Delegate to RagService."""
        return self.rag_service.pull_ollama_model(model_name)
