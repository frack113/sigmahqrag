#!/usr/bin/env python3
"""
Simple RAG CLI Tool with ChromaDB

A command-line interface for testing RAG functionality with local ChromaDB.
Provides commands for storing documents, querying, and checking ChromaDB status.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import colorama for colored terminal output
import colorama
from colorama import Fore, Back, Style

# Import existing services and utilities
from nicegui_app.models.rag_service_optimized import (
    OptimizedRAGService,
    create_rag_service
)
from nicegui_app.models.llm_service_optimized import (
    OptimizedLLMService,
    create_chat_service
)
from nicegui_app.models.repository_service import RepositoryService
from nicegui_app.models.data_service import DataService
from nicegui_app.models.logging_service import get_logger


class RAGCLI:
    """Command-line interface for RAG operations with ChromaDB."""
    
    def __init__(self, persist_directory: str = ".chromadb", base_url: str = "http://localhost:1234"):
        """
        Initialize the RAG CLI.
        
        Args:
            persist_directory: Directory to store ChromaDB data
            base_url: LM Studio server URL
        """
        # Configure logging to only write to file, not display in terminal for CLI
        import logging
        logging.getLogger().setLevel(logging.WARNING)  # Only show warnings and errors in terminal
        
        # Initialize colorama for cross-platform colored output
        colorama.init()
        
        self.persist_directory = persist_directory
        self.base_url = base_url
        
        # Use the centralized logging service with CLI-specific configuration
        from nicegui_app.models.logging_service import get_logger
        self.logger = get_logger(__name__)
        
        # Initialize services using factory functions for consistency
        self.llm_service = create_chat_service(
            base_url=base_url,
            temperature=0.7,
            max_tokens=512
        )
        
        self.rag_service = create_rag_service(
            llm_service=self.llm_service,
            base_url=base_url,
            persist_directory=persist_directory,
            collection_name="cli_rag_collection"
        )
    
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
            "llm_service_available": False
        }
        
        try:
            # Check if directory is writable
            if info["directory_exists"]:
                test_file = os.path.join(self.persist_directory, ".test_write")
                try:
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                    info["directory_writable"] = True
                except Exception:
                    info["directory_writable"] = False
            
            # Check LLM service
            try:
                # Try a simple test completion
                test_response = self.llm_service.simple_completion(
                    prompt="Hello",
                    system_prompt="You are a helpful assistant."
                )
                info["llm_service_available"] = True
                info["llm_test_response"] = test_response[:50] + "..." if len(test_response) > 50 else test_response
            except Exception as e:
                info["llm_service_error"] = str(e)
            
            # Check ChromaDB
            if self.rag_service.collection is not None:
                info["chromadb_available"] = True
                info["collection_stats"] = self.rag_service.get_context_stats()
                
        except Exception as e:
            info["error"] = str(e)
        
        return info
    
    def store_document(self, document_id: str, file_path: str, metadata: Optional[dict] = None) -> bool:
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
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if not content.strip():
                print(f"Error: File {file_path} is empty")
                return False
            
            # Store in vector database
            success = self.rag_service.store_context(
                document_id=document_id,
                text_content=content,
                metadata=metadata
            )
            
            if success:
                self._print_success(f"Successfully stored document '{document_id}' from {file_path}")
                stats = self.rag_service.get_context_stats()
                self._print_info(f"Total documents in collection: {stats.get('count', 0)}")
            else:
                self._print_error(f"Failed to store document '{document_id}'")
            
            return success
            
        except FileNotFoundError:
            print(f"Error: File not found: {file_path}")
            return False
        except Exception as e:
            print(f"Error storing document: {e}")
            return False
    
    def query(self, query_text: str, n_results: int = 3, min_score: float = 0.1) -> None:
        """
        Query the vector database and get RAG response.
        
        Args:
            query_text: The query text
            n_results: Number of results to retrieve
            min_score: Minimum similarity score threshold
        """
        try:
            print(f"Querying: '{query_text}'")
            print(f"Retrieving top {n_results} results (min score: {min_score})")
            print("-" * 50)
            
            # Get RAG response
            response = asyncio.run(
                self.rag_service.generate_rag_response(
                    query=query_text,
                    n_results=n_results,
                    min_relevance_score=min_score
                )
            )
            
            print("RAG Response:")
            print(response)
            print("-" * 50)
            
            # Also show retrieved context
            relevant_docs, metadata = self.rag_service.retrieve_context(
                query=query_text,
                n_results=n_results,
                min_relevance_score=min_score
            )
            
            if relevant_docs:
                print(f"Retrieved {len(relevant_docs)} relevant document chunks:")
                for i, (doc, meta) in enumerate(zip(relevant_docs, metadata), 1):
                    score = meta.get('similarity_score', 0)
                    doc_id = meta.get('document_id', 'unknown')
                    print(f"\n{i}. Document: {doc_id} (score: {score:.3f})")
                    print(f"   Content preview: {doc[:200]}{'...' if len(doc) > 200 else ''}")
            else:
                print("No relevant documents found in the vector database.")
                
        except Exception as e:
            print(f"Error during query: {e}")
    
    def list_documents(self) -> None:
        """List all stored documents and their metadata."""
        try:
            stats = self.rag_service.get_context_stats()
            count = stats.get('count', 0)
            
            if count == 0:
                print("No documents found in the vector database.")
                return
            
            print(f"Found {count} document chunks in the vector database:")
            print("-" * 50)
            
            # Note: ChromaDB doesn't have a direct "list all" method, 
            # so we'll use a query with empty string to get some results
            # or use the collection's get method if available
            try:
                # Try to get some sample documents
                results = self.rag_service.collection.get(
                    limit=min(10, count),
                    include=["metadatas", "documents"]
                )
                
                if results and results.get("metadatas"):
                    seen_docs = set()
                    for meta in results["metadatas"]:
                        doc_id = meta.get("document_id", "unknown")
                        if doc_id not in seen_docs:
                            seen_docs.add(doc_id)
                            chunk_count = meta.get("chunk_index", 0) + 1
                            print(f"Document ID: {doc_id}")
                            print(f"  Chunks: {chunk_count}")
                            print(f"  Source: {meta.get('source', 'unknown')}")
                            if "similarity_score" in meta:
                                print(f"  Last similarity score: {meta['similarity_score']}")
                            print()
                
                if not seen_docs:
                    print("Could not retrieve document details from ChromaDB.")
                    
            except Exception as e:
                print(f"Error retrieving document list: {e}")
                
        except Exception as e:
            print(f"Error getting document stats: {e}")
    
    def clear_database(self) -> bool:
        """Clear all documents from the vector database."""
        try:
            success = self.rag_service.clear_context()
            if success:
                self._print_success("Cleared all documents from the vector database.")
            else:
                self._print_error("Failed to clear the vector database.")
            return success
        except Exception as e:
            print(f"Error clearing database: {e}")
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
            print(f"Default chunk size: {rag_stats.get('default_chunk_size', 'unknown')}")
            print(f"Default chunk overlap: {rag_stats.get('default_chunk_overlap', 'unknown')}")
            print()
            print("Cache Statistics:")
            print(f"Total cache entries: {cache_stats.get('total_entries', 0)}")
            print(f"Valid entries: {cache_stats.get('valid_entries', 0)}")
            print(f"Expired entries: {cache_stats.get('expired_entries', 0)}")
            print(f"Cache size limit: {cache_stats.get('cache_size_limit', 'unknown')}")
            print(f"Cache TTL: {cache_stats.get('cache_ttl', 'unknown')} seconds")
            print()
            print(f"LLM Service Available: {llm_available}")
            
        except Exception as e:
            print(f"Error getting stats: {e}")
    
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
                print(f"Error: Configuration file not found: {config_file}")
                return False
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Initialize repository service
            repo_service = RepositoryService()
            
            print("Updating GitHub repositories...")
            print("-" * 50)
            
            # Clone/update enabled repositories
            success = asyncio.run(repo_service.clone_enabled_repositories(config))
            
            if success:
                self._print_success("GitHub repositories updated successfully")
                
                # Show repository information
                self._show_github_repos_info()
            else:
                self._print_error("Failed to update GitHub repositories")
            
            return success
            
        except Exception as e:
            print(f"Error updating GitHub repositories: {e}")
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
            print(f"Error getting repository info: {e}")
    
    def _get_repo_info(self, repo_dir: Path) -> dict:
        """Get information about a Git repository."""
        try:
            import git
            repo = git.Repo(str(repo_dir))
            
            # Get latest commit info
            latest_commit = repo.head.commit
            commit_date = latest_commit.committed_datetime.strftime("%Y-%m-%d %H:%M:%S")
            
            # Get branch info
            current_branch = repo.active_branch.name if hasattr(repo.active_branch, 'name') else "unknown"
            
            # Count files
            file_count = sum(1 for _ in repo_dir.rglob("*") if _.is_file())
            
            return {
                "Branch": current_branch,
                "Latest Commit": latest_commit.hexsha[:8],
                "Commit Date": commit_date,
                "Files": file_count
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
                print(f"Error: Configuration file not found: {config_file}")
                return False
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            print("Updating database by indexing repositories...")
            print("-" * 50)
            
            # First update GitHub repositories
            repo_service = RepositoryService()
            repo_success = asyncio.run(repo_service.clone_enabled_repositories(config))
            
            if not repo_success:
                print("✗ Failed to update GitHub repositories")
                return False
            
            # Then index the repositories
            repositories = config.get("repositories", [])
            if not repositories:
                print("No repositories found in configuration.")
                return False

            success_count = 0
            total_repos = len(repositories)

            for repo in repositories:
                if repo.get("enabled", True):
                    try:
                        success = self._index_single_repository(repo)
                        if success:
                            success_count += 1
                    except Exception as e:
                        print(f"Error indexing repository {repo.get('url')}: {e}")
                        continue

            if success_count > 0:
                self._print_success(f"Database updated successfully. Indexed {success_count}/{total_repos} enabled repositories.")
                
                # Show updated statistics
                stats = self.rag_service.get_context_stats()
                self._print_info(f"Total documents in collection: {stats.get('count', 0)}")
                self._print_info(f"Embedding model: {stats.get('embedding_model', 'unknown')}")
                return True
            else:
                self._print_error("No repositories were successfully indexed.")
                return False
                
        except Exception as e:
            print(f"Error updating database: {e}")
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
                print(f"Warning: Repository {url} missing URL or file extensions. Skipping.")
                return False

            # Extract repository name from URL
            parts = url.strip().split("/")
            if len(parts) < 5 or parts[2] != "github.com":
                print(f"Warning: Invalid GitHub repository URL: {url}")
                return False

            repo_name = parts[4]
            repo_dir = Path("data/github") / repo_name

            if not repo_dir.exists():
                print(f"Warning: Repository directory not found: {repo_dir}. Clone the repository first.")
                return False

            # Traverse the repository and process files
            processed_count = 0
            total_files = 0

            # First, count total files to process
            for file_path in repo_dir.rglob("*"):
                if file_path.is_file():
                    file_ext = file_path.suffix.lower()
                    if file_ext in file_extensions:
                        total_files += 1

            print(f"Found {total_files} files to process in repository {repo_name}")

            for file_path in repo_dir.rglob("*"):
                if file_path.is_file():
                    file_ext = file_path.suffix.lower()

                    # Check if file extension is allowed
                    if file_ext not in file_extensions:
                        continue

                    try:
                        # Show progress notification for each file
                        relative_path = file_path.relative_to(repo_dir)
                        print(f"Processing file: {relative_path}")

                        # Read file content
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                        except Exception as e:
                            print(f"  Warning: Could not read file {relative_path}: {e}")
                            continue

                        if not content.strip():
                            continue

                        # Create a unique document ID
                        doc_id = f"{repo_name}_{file_path.name}_{hash(str(file_path)) % 10000}"

                        # Prepare metadata
                        metadata = {
                            "repository": repo_name,
                            "branch": branch,
                            "file_path": str(relative_path),
                            "file_extension": file_ext,
                            "file_size": len(content),
                            "source": "github_repository"
                        }

                        # Store the context using RAG service
                        success = self.rag_service.store_context(doc_id, content, metadata)
                        if success:
                            processed_count += 1
                            print(f"  Successfully processed: {relative_path} ({processed_count}/{total_files})")
                        else:
                            print(f"  Failed to store: {relative_path}")

                    except Exception as e:
                        print(f"  Error processing file {relative_path}: {e}")
                        continue

            print(f"Indexed {processed_count} files from repository {repo_name}")
            return processed_count > 0
            
        except Exception as e:
            print(f"Error indexing repository: {e}")
            return False
    
    def run_interactive_mode(self) -> None:
        """
        Run the CLI in interactive mode with a continuous question-answer loop.
        
        The loop continues until the user types 'bye' or 'exit'.
        """
        self._print_header("🚀 Welcome to the RAG CLI Interactive Mode!")
        print("You can ask questions about the documents in the database.")
        print("Type 'bye' or 'exit' to quit the interactive session.")
        print("Type 'help' to see available commands.")
        print("=" * 60)
        
        # Show initial database status
        stats = self.rag_service.get_context_stats()
        self._print_info(f"Database Status: {stats.get('count', 0)} documents available")
        print()
        
        while True:
            try:
                # Get user input
                user_input = input("❓ Your question: ").strip()
                
                # Check for exit commands
                if user_input.lower() in ['bye', 'exit', 'quit', 'q']:
                    print("👋 Goodbye! Thanks for using the RAG CLI.")
                    break
                
                # Check for help
                if user_input.lower().strip() == 'help':
                    self._show_interactive_help()
                    continue
                
                # Check for empty input
                if not user_input:
                    print("💡 Please enter a question or type 'help' for assistance.")
                    continue
                
                # Process the query
                print()
                self.query(user_input, n_results=3, min_score=0.1)
                print()
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye! Thanks for using the RAG CLI.")
                break
            except EOFError:
                print("\n👋 Goodbye! Thanks for using the RAG CLI.")
                break
            except Exception as e:
                print(f"❌ Error processing your input: {e}")
                print("💡 Please try again or type 'bye' to exit.")
                print()
    
    def _show_interactive_help(self) -> None:
        """Show help information for interactive mode."""
        print("📚 Interactive Mode Help:")
        print("-" * 40)
        print("Commands:")
        print("  help          - Show this help message")
        print("  bye/exit/quit - Exit the interactive session")
        print("  q             - Quick exit")
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
    if sys.platform == 'win32':
        import os
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        sys.stdout.reconfigure(encoding='utf-8', errors='ignore')
        sys.stderr.reconfigure(encoding='utf-8', errors='ignore')
    
    parser = argparse.ArgumentParser(
        description="Simple RAG CLI with ChromaDB integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check ChromaDB information
  python rag_cli.py info
  
  # Store a document
  python rag_cli.py store --id doc1 --file document.txt
  
  # Query with RAG
  python rag_cli.py query "What is this document about?"
  
  # List stored documents
  python rag_cli.py list
  
  # Clear the database
  python rag_cli.py clear
  
  # Get system statistics
  python rag_cli.py stats
  
  # Update GitHub repositories
  python rag_cli.py github
  
  # Update database with repository content
  python rag_cli.py update-db
        """
    )
    
    parser.add_argument(
        "command",
        choices=["info", "store", "query", "list", "clear", "stats", "github", "update-db", "interactive"],
        help="Command to execute"
    )
    
    # Add a positional argument for query text
    parser.add_argument(
        "query_text",
        nargs="?",
        help="Query text (for query command)"
    )
    
    # Optional arguments
    parser.add_argument(
        "--persist-dir",
        default=".chromadb",
        help="Directory to store ChromaDB data (default: .chromadb)"
    )
    
    parser.add_argument(
        "--base-url",
        default="http://localhost:1234",
        help="LM Studio server URL (default: http://localhost:1234)"
    )
    
    # Store command arguments
    parser.add_argument(
        "--id",
        help="Document ID for storing documents"
    )
    
    parser.add_argument(
        "--file",
        help="File path for storing documents"
    )
    
    parser.add_argument(
        "--metadata",
        help="JSON string of metadata for the document"
    )
    
    # Query command arguments
    parser.add_argument(
        "--n-results",
        type=int,
        default=3,
        help="Number of results to retrieve (default: 3)"
    )
    
    parser.add_argument(
        "--min-score",
        type=float,
        default=0.1,
        help="Minimum similarity score threshold (default: 0.1)"
    )
    
    args = parser.parse_args()
    
    # Create CLI instance
    cli = RAGCLI(
        persist_directory=args.persist_dir,
        base_url=args.base_url
    )
    
    # Execute command
    if args.command == "info":
        info = cli.check_chromadb_info()
        print("ChromaDB Information:")
        print("=" * 50)
        for key, value in info.items():
            if key == "collection_stats" and value:
                print(f"{key}:")
                for k, v in value.items():
                    print(f"  {k}: {v}")
            elif key == "llm_test_response" and value:
                # Handle Unicode characters that might cause encoding issues
                safe_response = value.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
                print(f"{key}: {safe_response}")
            elif key != "collection_stats" and key != "llm_test_response":
                print(f"{key}: {value}")
    
    elif args.command == "store":
        if not args.id or not args.file:
            print("Error: --id and --file are required for store command")
            print("Usage: python rag_cli.py store --id <id> --file <path> [--metadata <json>]")
            sys.exit(1)
        
        metadata = None
        if args.metadata:
            try:
                metadata = json.loads(args.metadata)
            except json.JSONDecodeError as e:
                print(f"Error parsing metadata JSON: {e}")
                sys.exit(1)
        
        success = cli.store_document(args.id, args.file, metadata)
        sys.exit(0 if success else 1)
    
    elif args.command == "query":
        # For query command, we need to get the query text from remaining args
        # Find the position of 'query' in sys.argv
        try:
            query_index = sys.argv.index("query")
            query_text = " ".join(sys.argv[query_index+1:])
            
            if not query_text.strip():
                print("Error: Query text is required")
                print("Usage: python rag_cli.py query <query_text> [--n-results N] [--min-score S]")
                sys.exit(1)
            
            cli.query(query_text, args.n_results, args.min_score)
        except ValueError:
            print("Error: Query command not found in arguments")
            print("Usage: python rag_cli.py query <query_text> [--n-results N] [--min-score S]")
            sys.exit(1)
    
    elif args.command == "list":
        cli.list_documents()
    
    elif args.command == "clear":
        success = cli.clear_database()
        sys.exit(0 if success else 1)
    
    elif args.command == "stats":
        cli.get_stats()
    
    elif args.command == "github":
        success = cli.update_github_repos()
        sys.exit(0 if success else 1)
    
    elif args.command == "update-db":
        success = cli.update_database()
        sys.exit(0 if success else 1)
    
    elif args.command == "interactive":
        cli.run_interactive_mode()
    
    else:
        print(f"Unknown command: {args.command}")
        sys.exit(1)


if __name__ == "__main__":
    main()