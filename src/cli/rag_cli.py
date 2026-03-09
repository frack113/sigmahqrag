#!/usr/bin/env python3
"""
Optimized RAG CLI Tool with ChromaDB

An optimized command-line interface for testing RAG functionality with local ChromaDB.
Provides commands for storing documents, querying, and checking ChromaDB status with
improved performance, error handling, and user experience.
"""

import argparse
import asyncio
import json
import os
import sys
import time
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from contextlib import contextmanager
import logging

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import colorama for colored terminal output
import colorama
from colorama import Fore, Back, Style

# Import existing services and utilities
from nicegui_app.models.rag_service_optimized import (
    OptimizedRAGService,
    create_rag_service,
)
from nicegui_app.models.llm_service_optimized import (
    OptimizedLLMService,
    create_chat_service,
)
from nicegui_app.models.repository_service import RepositoryService
from nicegui_app.models.data_service import DataService
from nicegui_app.models.logging_service import get_logger
from nicegui_app.models.config_service import ConfigService


@dataclass
class ProcessingResult:
    """Result of a file processing operation."""
    success: bool
    file_path: str
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class OptimizedRAGCLI:
    """Optimized command-line interface for RAG operations with ChromaDB."""

    def __init__(self):
        """
        Initialize the optimized RAG CLI.
        """
        # Initialize colorama for cross-platform colored output
        colorama.init()

        # Initialize ConfigService for configuration management
        self.config_service = ConfigService()

        # Get configuration from ConfigService
        config = self.config_service.get_config_with_defaults()
        rag_config = config.get("rag", {})
        llm_config = config.get("llm", {})
        performance_config = config.get("performance", {})

        self.persist_directory = rag_config.get("persist_directory", ".chromadb")
        self.base_url = llm_config.get("base_url", "http://localhost:1234")
        
        # Performance configuration
        self.max_workers = performance_config.get("max_workers", 4)
        self.chunk_size = rag_config.get("chunk_size", 1000)
        self.chunk_overlap = rag_config.get("chunk_overlap", 200)

        # Use the centralized logging service with CLI-specific configuration
        self.logger = get_logger(__name__)

        # Initialize services using factory functions for consistency
        self.llm_service = create_chat_service(
            base_url=self.base_url,
            temperature=llm_config.get("temperature", 0.7),
            max_tokens=llm_config.get("max_tokens", 512),
        )

        self.rag_service = create_rag_service(
            llm_service=self.llm_service,
            base_url=self.base_url,
            persist_directory=self.persist_directory,
            collection_name="cli_rag_collection",
        )

        # Performance tracking
        self._processing_times = []
        self._last_query_time = 0

    def _print_success(self, message: str) -> None:
        """Print a success message with green color."""
        print(f"{Fore.GREEN}✓ {message}{Style.RESET_ALL}")

    def _print_error(self, message: str) -> None:
        """Print an error message with red color."""
        print(f"{Fore.RED}✗ {message}{Style.RESET_ALL}")

    def _print_info(self, message: str) -> None:
        """Print an info message with blue color."""
        print(f"{Fore.BLUE}ℹ {message}{Style.RESET_ALL}")

    def _print_warning(self, message: str) -> None:
        """Print a warning message with yellow color."""
        print(f"{Fore.YELLOW}⚠ {message}{Style.RESET_ALL}")

    def _print_header(self, message: str) -> None:
        """Print a header with cyan color and underline."""
        print(f"{Fore.CYAN}{Style.BRIGHT}{message}{Style.RESET_ALL}")

    def _print_section(self, message: str) -> None:
        """Print a section header with magenta color."""
        print(f"{Fore.MAGENTA}{Style.BRIGHT}{message}{Style.RESET_ALL}")

    def _print_progress(self, message: str) -> None:
        """Print a progress message with white color."""
        print(f"{Fore.WHITE}⏳ {message}{Style.RESET_ALL}")

    @contextmanager
    def _timing_context(self, operation_name: str):
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            end_time = time.time()
            duration = end_time - start_time
            self._processing_times.append((operation_name, duration))
            self._print_info(f"{operation_name} completed in {duration:.2f}s")

    def check_chromadb_info(self) -> dict:
        """
        Get detailed information about ChromaDB setup and status.

        Returns:
            Dictionary with ChromaDB information
        """
        info = {
            "chromadb_available": False,
            "persist_directory": self.persist_directory,
            "collection_name": "cli_rag_collection",
            "base_url": self.base_url,
            "directory_exists": os.path.exists(self.persist_directory),
            "directory_writable": False,
            "collection_stats": {},
            "llm_service_available": False,
            "performance_metrics": {
                "avg_processing_time": 0,
                "total_operations": len(self._processing_times)
            }
        }

        try:
            # Check if directory is writable
            if info["directory_exists"]:
                test_file = os.path.join(self.persist_directory, ".test_write")
                try:
                    with open(test_file, "w") as f:
                        f.write("test")
                    os.remove(test_file)
                    info["directory_writable"] = True
                except Exception:
                    info["directory_writable"] = False

            # Check LLM service
            try:
                # Try a simple test completion
                test_response = self.llm_service.simple_completion(
                    prompt="Hello", system_prompt="You are a helpful assistant."
                )
                info["llm_service_available"] = True
                info["llm_test_response"] = (
                    test_response[:50] + "..."
                    if len(test_response) > 50
                    else test_response
                )
            except Exception as e:
                info["llm_service_error"] = str(e)

            # Check ChromaDB
            if self.rag_service.collection is not None:
                info["chromadb_available"] = True
                info["collection_stats"] = self.rag_service.get_context_stats()

            # Calculate performance metrics
            if self._processing_times:
                avg_time = sum(time for _, time in self._processing_times) / len(self._processing_times)
                info["performance_metrics"]["avg_processing_time"] = avg_time

        except Exception as e:
            info["error"] = str(e)

        return info

    def store_document(
        self, document_id: str, file_path: str, metadata: Optional[dict] = None
    ) -> bool:
        """
        Store a document in the vector database.

        Args:
            document_id: Unique identifier for the document
            file_path: Path to the text file to store
            metadata: Optional metadata for the document

        Returns:
            True if successful, False otherwise
        """
        try:
            # Read file content
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if not content.strip():
                self._print_warning(f"File {file_path} is empty")
                return False

            # Store in vector database
            with self._timing_context(f"Storing document '{document_id}'"):
                success = self.rag_service.store_context(
                    document_id=document_id, text_content=content, metadata=metadata
                )

            if success:
                self._print_success(
                    f"Successfully stored document '{document_id}' from {file_path}"
                )
                stats = self.rag_service.get_context_stats()
                self._print_info(
                    f"Total documents in collection: {stats.get('count', 0)}"
                )
            else:
                self._print_error(f"Failed to store document '{document_id}'")

            return success

        except FileNotFoundError:
            self._print_error(f"File not found: {file_path}")
            return False
        except Exception as e:
            self._print_error(f"Error storing document: {e}")
            return False

    def query(
        self, query_text: str, n_results: int = 3, min_score: float = 0.1
    ) -> None:
        """
        Query the vector database and get RAG response.

        Args:
            query_text: The query text
            n_results: Number of results to retrieve
            min_score: Minimum similarity score threshold
        """
        try:
            # Check if database has documents
            stats = self.rag_service.get_context_stats()
            total_docs = stats.get("count", 0)

            if total_docs == 0:
                self._print_warning(
                    "No documents found in the database. Please store some documents first."
                )
                print(
                    "💡 Try: store a document or use 'update-db' to index repositories"
                )
                return

            # Get RAG response
            with self._timing_context("Query processing"):
                response = asyncio.run(
                    self.rag_service.generate_rag_response(
                        query=query_text, n_results=n_results, min_relevance_score=min_score
                    )
                )

            # Show RAG response with header only
            print("🤖 RAG Response:")
            print(response)

        except Exception as e:
            self._print_error(f"Error during query: {e}")
            print("💡 Please try a different query or check the database status.")

    def clear_database(self) -> bool:
        """Clear all documents from the vector database."""
        try:
            with self._timing_context("Clearing database"):
                success = self.rag_service.clear_context()
            
            if success:
                self._print_success("Cleared all documents from the vector database.")
            else:
                self._print_error("Failed to clear the vector database.")
            return success
        except Exception as e:
            self._print_error(f"Error clearing database: {e}")
            return False

    def get_stats(self) -> None:
        """Get detailed statistics about the RAG system."""
        try:
            # ChromaDB stats
            rag_stats = self.rag_service.get_context_stats()

            # Cache stats
            cache_stats = self.rag_service.get_cache_stats()

            # LLM service check
            llm_available = self.rag_service.check_availability()

            print("RAG System Statistics:")
            print("=" * 50)
            print(f"ChromaDB Collection: {rag_stats.get('collection_name', 'unknown')}")
            print(f"Documents in collection: {rag_stats.get('count', 0)}")
            print(f"Embedding model: {rag_stats.get('embedding_model', 'unknown')}")
            print(f"Persist directory: {rag_stats.get('persist_directory', 'unknown')}")
            print(
                f"Default chunk size: {rag_stats.get('default_chunk_size', 'unknown')}"
            )
            print(
                f"Default chunk overlap: {rag_stats.get('default_chunk_overlap', 'unknown')}"
            )
            print()
            print("Cache Statistics:")
            print(f"Total cache entries: {cache_stats.get('total_entries', 0)}")
            print(f"Valid entries: {cache_stats.get('valid_entries', 0)}")
            print(f"Expired entries: {cache_stats.get('expired_entries', 0)}")
            print(f"Cache size limit: {cache_stats.get('cache_size_limit', 'unknown')}")
            print(f"Cache TTL: {cache_stats.get('cache_ttl', 'unknown')} seconds")
            print()
            print(f"LLM Service Available: {llm_available}")
            
            # Performance metrics
            if self._processing_times:
                avg_time = sum(time for _, time in self._processing_times) / len(self._processing_times)
                print(f"Average processing time: {avg_time:.2f}s")
                print(f"Total operations: {len(self._processing_times)}")

        except Exception as e:
            self._print_error(f"Error getting stats: {e}")

    def update_github_repos(self, config_file: str = "data/config.json") -> bool:
        """
        Update GitHub repositories based on configuration.

        Args:
            config_file: Path to the configuration file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load configuration
            if not os.path.exists(config_file):
                self._print_error(f"Configuration file not found: {config_file}")
                return False

            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Initialize repository service
            repo_service = RepositoryService()

            self._print_progress("Updating GitHub repositories...")
            print("-" * 50)

            # Clone/update enabled repositories
            with self._timing_context("GitHub repository update"):
                success = asyncio.run(repo_service.clone_enabled_repositories(config))

            if success:
                self._print_success("GitHub repositories updated successfully")

                # Show repository information
                self._show_github_repos_info()
            else:
                self._print_error("Failed to update GitHub repositories")

            return success

        except Exception as e:
            self._print_error(f"Error updating GitHub repositories: {e}")
            return False

    def _show_github_repos_info(self) -> None:
        """Show information about cloned GitHub repositories."""
        try:
            github_dir = Path("data/github")
            if not github_dir.exists():
                print("No GitHub repositories found")
                return

            print(f"\nGitHub Repositories in {github_dir}:")
            print("-" * 50)

            for repo_dir in github_dir.iterdir():
                if repo_dir.is_dir():
                    # Get repository info
                    repo_info = self._get_repo_info(repo_dir)
                    print(f"Repository: {repo_dir.name}")
                    if repo_info:
                        for key, value in repo_info.items():
                            print(f"  {key}: {value}")
                    print()

        except Exception as e:
            self._print_error(f"Error getting repository info: {e}")

    def _get_repo_info(self, repo_dir: Path) -> dict:
        """Get information about a Git repository."""
        try:
            import git

            repo = git.Repo(str(repo_dir))

            # Get latest commit info
            latest_commit = repo.head.commit
            commit_date = latest_commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S")

            # Get branch info
            current_branch = (
                repo.active_branch.name
                if hasattr(repo.active_branch, "name")
                else "unknown"
            )

            # Count files
            file_count = sum(1 for _ in repo_dir.rglob("*") if _.is_file())

            return {
                "Branch": current_branch,
                "Latest Commit": latest_commit.hexsha[:8],
                "Commit Date": commit_date,
                "Files": file_count,
            }

        except Exception as e:
            return {"Error": str(e)}

    def update_database(self, config_file: str = "data/config.json") -> bool:
        """
        Update the database by indexing enabled repositories.

        This uses the existing repository service to process files from GitHub repositories
        and store them in the vector database for RAG operations.

        Args:
            config_file: Path to the configuration file

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load configuration
            if not os.path.exists(config_file):
                self._print_error(f"Configuration file not found: {config_file}")
                return False

            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            self._print_progress("Updating database by indexing repositories...")
            print("-" * 50)

            # First update GitHub repositories
            repo_service = RepositoryService()
            with self._timing_context("Repository cloning"):
                repo_success = asyncio.run(repo_service.clone_enabled_repositories(config))

            if not repo_success:
                self._print_error("Failed to update GitHub repositories")
                return False

            # Then index the repositories
            repositories = config.get("repositories", [])
            if not repositories:
                self._print_warning("No repositories found in configuration.")
                return False

            success_count = 0
            total_repos = len(repositories)

            with self._timing_context(f"Indexing {total_repos} repositories"):
                for repo in repositories:
                    if repo.get("enabled", True):
                        try:
                            success = self._index_single_repository(repo)
                            if success:
                                success_count += 1
                        except Exception as e:
                            self._print_error(f"Error indexing repository {repo.get('url')}: {e}")
                            continue

            if success_count > 0:
                self._print_success(
                    f"Database updated successfully. Indexed {success_count}/{total_repos} enabled repositories."
                )

                # Show updated statistics
                stats = self.rag_service.get_context_stats()
                self._print_info(
                    f"Total documents in collection: {stats.get('count', 0)}"
                )
                self._print_info(
                    f"Embedding model: {stats.get('embedding_model', 'unknown')}"
                )
                return True
            else:
                self._print_error("No repositories were successfully indexed.")
                return False

        except Exception as e:
            self._print_error(f"Error updating database: {e}")
            return False

    def _index_single_repository(self, repo_config: dict) -> bool:
        """
        Index a single repository by processing files based on allowed extensions.

        Args:
            repo_config: Configuration for the repository

        Returns:
            True if indexing was successful, False otherwise
        """
        try:
            url = repo_config.get("url")
            branch = repo_config.get("branch", "main")
            file_extensions = repo_config.get("file_extensions", [])

            if not url or not file_extensions:
                self._print_warning(f"Repository {url} missing URL or file extensions. Skipping.")
                return False

            # Extract repository name from URL
            parts = url.strip().split("/")
            if len(parts) < 5 or parts[2] != "github.com":
                self._print_warning(f"Invalid GitHub repository URL: {url}")
                return False

            repo_name = parts[4]
            repo_dir = Path("data/github") / repo_name

            if not repo_dir.exists():
                self._print_warning(f"Repository directory not found: {repo_dir}. Clone the repository first.")
                return False

            # Traverse the repository and process files
            processed_count = 0
            total_files = 0

            # First, count total files to process
            with self._timing_context(f"Counting files in {repo_name}"):
                for file_path in repo_dir.rglob("*"):
                    if file_path.is_file():
                        file_ext = file_path.suffix.lower()
                        if file_ext in file_extensions:
                            total_files += 1

            if total_files == 0:
                self._print_warning(f"No files found to process in repository {repo_name}")
                return False

            self._print_info(f"Found {total_files} files to process in repository {repo_name}")

            # Process files with progress tracking
            results = []
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all file processing tasks
                future_to_file = {}
                for file_path in repo_dir.rglob("*"):
                    if file_path.is_file():
                        file_ext = file_path.suffix.lower()
                        if file_ext in file_extensions:
                            future = executor.submit(
                                self._process_single_file,
                                file_path, repo_name, branch, file_ext
                            )
                            future_to_file[future] = file_path

                # Collect results as they complete
                with self._timing_context(f"Processing {total_files} files"):
                    for future in as_completed(future_to_file):
                        result = future.result()
                        results.append(result)
                        if result.success:
                            processed_count += 1
                            relative_path = result.file_path.relative_to(repo_dir)
                            print(f"  ✓ {relative_path} ({processed_count}/{total_files})")
                        else:
                            relative_path = result.file_path.relative_to(repo_dir)
                            print(f"  ✗ {relative_path}: {result.error_message}")

            print(f"Indexed {processed_count} files from repository {repo_name}")
            return processed_count > 0

        except Exception as e:
            self._print_error(f"Error indexing repository: {e}")
            return False

    def _process_single_file(
        self, file_path: Path, repo_name: str, branch: str, file_ext: str
    ) -> ProcessingResult:
        """
        Process a single file for indexing.

        Args:
            file_path: Path to the file to process
            repo_name: Name of the repository
            branch: Branch name
            file_ext: File extension

        Returns:
            ProcessingResult indicating success or failure
        """
        try:
            # Show progress notification for each file
            relative_path = file_path.relative_to(Path("data/github") / repo_name)

            # Read file content
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except Exception as e:
                return ProcessingResult(
                    success=False,
                    file_path=file_path,
                    error_message=f"Could not read file: {e}"
                )

            if not content.strip():
                return ProcessingResult(
                    success=False,
                    file_path=file_path,
                    error_message="File is empty"
                )

            # Create a unique document ID
            doc_id = f"{repo_name}_{file_path.name}_{hash(str(file_path)) % 10000}"

            # Prepare metadata
            metadata = {
                "repository": repo_name,
                "branch": branch,
                "file_path": str(relative_path),
                "file_extension": file_ext,
                "file_size": len(content),
                "source": "github_repository",
            }

            # Store the context using RAG service
            success = self.rag_service.store_context(doc_id, content, metadata)
            
            return ProcessingResult(
                success=success,
                file_path=file_path,
                metadata=metadata if success else None,
                error_message=None if success else "Failed to store in database"
            )

        except Exception as e:
            return ProcessingResult(
                success=False,
                file_path=file_path,
                error_message=str(e)
            )

    def run_interactive_mode(self) -> None:
        """
        Run the CLI in interactive mode with a continuous question-answer loop.

        The loop continues until the user types 'bye' or 'exit'.
        """
        self._print_header("🚀 Welcome to the Optimized RAG CLI Interactive Mode!")
        print("You can ask questions about the documents in the database.")
        print("Type 'bye' or 'exit' to quit the interactive session.")
        print("Type 'help' to see available commands.")
        print("=" * 60)

        # Show initial database status
        stats = self.rag_service.get_context_stats()
        total_docs = stats.get("count", 0)
        if total_docs > 0:
            self._print_success(f"Database Status: {total_docs} documents available")
        else:
            self._print_warning("Database Status: No documents available")
        print()

        # Show tips for better queries
        print("💡 Tips for better results:")
        print("  • Be specific in your questions")
        print("  • Use keywords from the documents")
        print("  • Try different phrasings if needed")
        print("  • Use 'stats' to check database status")
        print("-" * 60)
        print()

        while True:
            try:
                # Get user input with improved prompt
                user_input = input("❓ Ask a question or type a command: ").strip()

                # Check for exit commands
                if user_input.lower() in ["bye", "exit", "quit", "q"]:
                    print("👋 Goodbye! Thanks for using the Optimized RAG CLI.")
                    break

                # Check for help
                if user_input.lower().strip() == "help":
                    self._show_interactive_help()
                    continue

                # Check for empty input
                if not user_input:
                    print("💡 Please enter a question or type 'help' for assistance.")
                    continue

                # Process special commands
                command_parts = user_input.lower().split()
                if command_parts:
                    command = command_parts[0]

                    if command == "clear":
                        success = self.clear_database()
                        if success:
                            stats = self.rag_service.get_context_stats()
                            self._print_info(
                                f"Database cleared. Total documents now: {stats.get('count', 0)}"
                            )
                        continue

                    elif command == "stats":
                        self.get_stats()
                        continue

                    elif command == "info":
                        self.show_system_info()
                        continue

                    elif command == "github":
                        success = self.update_github_repos()
                        if success:
                            stats = self.rag_service.get_context_stats()
                            self._print_info(
                                f"GitHub repositories updated. Total documents: {stats.get('count', 0)}"
                            )
                        continue

                    elif command == "update-db":
                        success = self.update_database()
                        if success:
                            stats = self.rag_service.get_context_stats()
                            self._print_info(
                                f"Database updated. Total documents: {stats.get('count', 0)}"
                            )
                        continue

                    elif command == "performance":
                        self._show_performance_metrics()
                        continue

                # Process the query with enhanced feedback
                print()
                print("🔍 Processing your query...")
                self.query(user_input, n_results=3, min_score=0.1)
                print()

            except KeyboardInterrupt:
                print("\n👋 Goodbye! Thanks for using the Optimized RAG CLI.")
                break
            except EOFError:
                print("\n👋 Goodbye! Thanks for using the Optimized RAG CLI.")
                break
            except Exception as e:
                self._print_error(f"Error processing your input: {e}")
                print("💡 Please try again or type 'bye' to exit.")
                print()

    def show_system_info(self) -> None:
        """Show comprehensive system information using ConfigService."""
        try:
            self._print_header("📋 System Information")
            print("=" * 60)

            # Get configuration from ConfigService
            config = self.config_service.get_config_with_defaults()
            rag_config = config.get("rag", {})
            llm_config = config.get("llm", {})
            performance_config = config.get("performance", {})

            # Show LLM Configuration
            self._print_section("🤖 LLM Configuration")
            print(f"Model: {llm_config.get('model', 'unknown')}")
            print(f"Base URL: {llm_config.get('base_url', 'unknown')}")
            print(f"Temperature: {llm_config.get('temperature', 'unknown')}")
            print(f"Max Tokens: {llm_config.get('max_tokens', 'unknown')}")

            # Check LLM service availability
            try:
                test_response = self.llm_service.simple_completion(
                    prompt="Hello", system_prompt="You are a helpful assistant."
                )
                self._print_success("LLM Service: Available")
                print(
                    f"Test Response: {test_response[:50]}{'...' if len(test_response) > 50 else ''}"
                )
            except Exception as e:
                self._print_error(f"LLM Service: Unavailable - {e}")

            print()

            # Show RAG Configuration
            self._print_section("🗄️  RAG Configuration")
            print(
                f"Persist Directory: {rag_config.get('persist_directory', 'unknown')}"
            )
            print(f"Embedding Model: {rag_config.get('embedding_model', 'unknown')}")
            print(f"Chunk Size: {rag_config.get('chunk_size', 'unknown')}")
            print(f"Chunk Overlap: {rag_config.get('chunk_overlap', 'unknown')}")
            print(f"Cache Size: {rag_config.get('cache_size', 'unknown')}")
            print(f"Cache TTL: {rag_config.get('cache_ttl', 'unknown')} seconds")

            # Check ChromaDB availability
            try:
                stats = self.rag_service.get_context_stats()
                if stats.get("count", 0) > 0:
                    self._print_success(
                        f"ChromaDB: Available ({stats.get('count', 0)} documents)"
                    )
                else:
                    self._print_warning("ChromaDB: Available (0 documents)")
            except Exception as e:
                self._print_error(f"ChromaDB: Unavailable - {e}")

            print()

            # Show Performance Configuration
            self._print_section("⚡ Performance Configuration")
            print(f"Max Workers: {performance_config.get('max_workers', 'unknown')}")
            print(
                f"Thread Pool Size: {performance_config.get('thread_pool_size', 'unknown')}"
            )
            print(
                f"Request Timeout: {performance_config.get('request_timeout', 'unknown')} seconds"
            )

            print()

            # Show Repository Configuration
            self._print_section("📦 Repository Configuration")
            repositories = self.config_service.get_repositories()
            enabled_repos = self.config_service.get_enabled_repositories()

            print(f"Total Repositories: {len(repositories)}")
            print(f"Enabled Repositories: {len(enabled_repos)}")

            if repositories:
                print("\nRepositories:")
                for i, repo in enumerate(repositories, 1):
                    status = "✅ Enabled" if repo.enabled else "❌ Disabled"
                    print(f"  {i}. {repo.url}")
                    print(f"     Branch: {repo.branch}")
                    print(f"     Status: {status}")
                    print(
                        f"     Extensions: {', '.join(repo.file_extensions) if repo.file_extensions else 'None'}"
                    )
                    print()
            else:
                print("No repositories configured.")

            print()

            # Show GitHub Directory Status
            self._print_section("📁 GitHub Directory Status")
            github_dir = Path("data/github")
            if github_dir.exists():
                repo_dirs = [d for d in github_dir.iterdir() if d.is_dir()]
                print(f"GitHub Directory: {github_dir} (exists)")
                print(f"Cloned Repositories: {len(repo_dirs)}")
                if repo_dirs:
                    for repo_dir in repo_dirs:
                        try:
                            import git

                            repo = git.Repo(str(repo_dir))
                            latest_commit = repo.head.commit.hexsha[:8]
                            print(f"  • {repo_dir.name}: {latest_commit}")
                        except Exception:
                            print(f"  • {repo_dir.name}: (error reading)")
                else:
                    print("  No repositories cloned yet.")
            else:
                print(f"GitHub Directory: {github_dir} (does not exist)")

            print()

            # Show Cache Statistics
            self._print_section("💾 Cache Statistics")
            cache_stats = self.rag_service.get_cache_stats()
            print(f"Total Cache Entries: {cache_stats.get('total_entries', 0)}")
            print(f"Valid Entries: {cache_stats.get('valid_entries', 0)}")
            print(f"Expired Entries: {cache_stats.get('expired_entries', 0)}")

            print()

            # Show Performance Metrics
            self._show_performance_metrics()

            print()
            print("=" * 60)

        except Exception as e:
            self._print_error(f"Error getting system information: {e}")

    def _show_performance_metrics(self) -> None:
        """Show performance metrics and optimization suggestions."""
        self._print_section("📊 Performance Metrics")
        
        if self._processing_times:
            avg_time = sum(time for _, time in self._processing_times) / len(self._processing_times)
            min_time = min(time for _, time in self._processing_times)
            max_time = max(time for _, time in self._processing_times)
            
            print(f"Average processing time: {avg_time:.2f}s")
            print(f"Fastest operation: {min_time:.2f}s")
            print(f"Slowest operation: {max_time:.2f}s")
            print(f"Total operations: {len(self._processing_times)}")
            
            # Show operation breakdown
            operation_counts = {}
            for op_name, _ in self._processing_times:
                operation_counts[op_name] = operation_counts.get(op_name, 0) + 1
            
            print("\nOperation breakdown:")
            for op_name, count in operation_counts.items():
                print(f"  {op_name}: {count} times")
        else:
            print("No performance data available yet.")

    def _show_interactive_help(self) -> None:
        """Show help information for interactive mode."""
        print("📚 Interactive Mode Help:")
        print("-" * 40)
        print("Commands:")
        print("  help          - Show this help message")
        print("  bye/exit/quit - Exit the interactive session")
        print("  q             - Quick exit")
        print("  clear         - Clear all documents from the database")
        print("  stats         - Show detailed system statistics")
        print("  info          - Show comprehensive system information")
        print("  github        - Update GitHub repositories")
        print("  update-db     - Update database with repository content")
        print("  performance   - Show performance metrics")
        print()
        print("Tips:")
        print("  • Ask questions about the documents in the database")
        print("  • Be specific for better results")
        print("  • The system will retrieve relevant document chunks")
        print("  • Responses are generated using RAG (Retrieval-Augmented Generation)")
        print("  • Type 'bye' when you're done")
        print("-" * 40)
        print()


def main():
    """Main CLI entry point."""
    # Set UTF-8 encoding for Windows compatibility
    import sys

    if sys.platform == "win32":
        import os

        os.environ["PYTHONIOENCODING"] = "utf-8"
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
        sys.stderr.reconfigure(encoding="utf-8", errors="ignore")

    # Always start in interactive mode - no command-line arguments needed
    print("🚀 Starting Optimized RAG CLI in interactive mode...")
    print("💡 Type 'help' for available commands or 'bye' to exit.")
    print()

    # Create CLI instance using ConfigService
    cli = OptimizedRAGCLI()

    # Start interactive mode directly
    cli.run_interactive_mode()


if __name__ == "__main__":
    main()