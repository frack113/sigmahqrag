"""
Data Service - Optimized for Gradio Native Integration

Uses simple methods without custom async wrappers:
- Direct file operations
- Simple subprocess calls (Gradio handles async via queue=True)
- No asyncio overhead
"""

import json
from pathlib import Path
from typing import Any

from src.shared.constants import (
    DATA_CHROMA_PATH,
    DATA_GITHUB_PATH,
    TEMP_DIR_PATH,
)


class DataService:
    """
    Data service using simple file operations.

    Features:
    - Repository/local path indexing
    - Context management for RAG
    - Simple synchronous methods (Gradio queue=True handles async)
    """

    def __init__(self):

        # Use DATA_* constants directly - they already include "data/" prefix
        self.github_path = Path(DATA_GITHUB_PATH)
        self.chroma_db_path = Path(DATA_CHROMA_PATH)
        self.temp_dir = Path(TEMP_DIR_PATH)

        # Ensure directories exist
        self.github_path.mkdir(parents=True, exist_ok=True)
        self.chroma_db_path.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def index_repository(self, repo_config: dict[str, Any]) -> bool:
        """Index a repository or local path.

        Args:
            repo_config: Dictionary containing 'url' (path to scan) and
                        'file_extensions' list of extensions to index.
        """
        try:
            url = repo_config.get("url", "")
            file_extensions = repo_config.get("file_extensions", [])

            # Determine the path to index
            if not Path(url).is_absolute():
                # Convert relative path like 'docs/USER_DOCUMENTATION' to absolute

                base_dir = Path(DATA_GITHUB_PATH)  # Use constant with "data/" prefix
                url = str(Path(base_dir) / Path(url))

            path_to_index = Path(url)

            if not path_to_index.exists():
                print(f"Path does not exist: {url}")
                return False

            print(f"Indexing repository: {url}")

            # Collect files to index based on extensions
            files_to_index = []

            # If no specific extensions, use defaults
            if not file_extensions:
                file_extensions = [
                    "py",
                    "md",
                    "yml",
                    "yaml",
                    "json",
                    "toml",
                    "txt",
                    "sh",
                ]

            for ext in file_extensions:
                # Find files recursively
                files = list(path_to_index.rglob(f"*.{ext}"))
                files_to_index.extend(files)

            print(f"Found {len(files_to_index)} files to index")

            # Copy files to github directory for unified indexing
            import shutil

            repo_name = Path(url).name if url else "repo"
            dest_path = self.github_path / repo_name

            dest_path.mkdir(exist_ok=True)

            for src_file in files_to_index:
                try:
                    # Create destination path preserving relative structure
                    rel_path = src_file.relative_to(path_to_index)
                    dest_file = dest_path / rel_path

                    # Ensure parent directory exists
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    # Copy file content
                    shutil.copy2(str(src_file), str(dest_file))
                except Exception as e:
                    print(f"Error copying {src_file}: {e}")

            return True

        except Exception as e:
            print(f"Index failed: {e}")
            return False

    def index_enabled_repositories(self, repo_config: dict[str, Any]) -> bool:
        """Index all enabled repositories."""
        repos = repo_config.get("repositories", [])
        indexed_count = 0

        for repo in repos:
            if not repo.get("enabled", False):
                continue

            print(f"Processing repository: {repo['url']}")

            success = self.index_repository(repo)

            if success:
                indexed_count += 1

        print(f"Indexed {indexed_count} repositories")
        return indexed_count > 0

    def reset_database(self) -> bool:
        """Reset database by clearing ONLY the ChromaDB vector database (NOT indexed files)."""
        try:
            # Clear ChromaDB collection ONLY - indexed files in github_path are preserved
            try:
                from chromadb import PersistentClient
                from chromadb.errors import NotFoundError

                if self.chroma_db_path.exists():
                    client = PersistentClient(path=str(self.chroma_db_path))
                    try:
                        # Delete the collection without removing the database file
                        client.delete_collection(name="documents")
                        print("ChromaDB collection 'documents' cleared")
                        return True
                    except NotFoundError:
                        # Collection doesn't exist yet (first run) - nothing to clear
                        print(
                            "ChromaDB collection 'documents' not found - this is expected on first run"
                        )
                        return True
            except Exception as e:
                print(f"Could not clear ChromaDB collection: {e}")

            return False
        except Exception as e:
            print(f"Reset failed: {e}")
            return False

    def get_context_stats(self) -> dict[str, Any]:
        """Get context statistics from indexed files."""
        try:
            # Use the github_path that was set in __init__ (same path as index_repository uses)
            count = 0
            total_size = 0

            extensions = {"py", "md", "yml", "yaml", "json", "toml"}

            for repo_dir in self.github_path.iterdir():
                if repo_dir.is_dir():
                    for ext in sorted(extensions):
                        files = list(repo_dir.glob(f"**/*.{ext}"))
                        count += len(files)
                        total_size += sum(f.stat().st_size for f in files)

            return {
                "count": count,
                "size_mb": round(total_size / (1024 * 1024), 2),
                "embedding_model": "all-MiniLM-L6-v2",
                "default_chunk_size": 1000,
                "default_chunk_overlap": 200,
            }

        except Exception:
            return {
                "count": 0,
                "size_mb": 0,
                "embedding_model": "Unknown",
                "default_chunk_size": 1000,
                "default_chunk_overlap": 200,
            }

    def get_repo_config(self) -> dict[str, Any]:
        """Load repository configuration from data/config.json."""
        try:

            # Get absolute path to data/config.json
            config_path = Path("data/config.json")

            if not config_path.exists():
                return {"repositories": []}

            with open(config_path, encoding="utf-8") as f:
                data = json.load(f)

            # The config structure can be in different locations:
            # 1. Directly under "repositories" (expected format)
            # 2. Under "network.repositories" (current config format)

            if "repositories" in data and isinstance(data["repositories"], list):
                return {"repositories": data["repositories"]}

            if "network" in data and isinstance(data["network"], dict):
                network_data = data["network"]
                if "repositories" in network_data:
                    return {"repositories": network_data["repositories"]}

            return {"repositories": []}

        except Exception as e:
            print(f"Error loading repo config: {e}")
            return {"repositories": []}

    def reindex_vector_db(self) -> bool:
        """Re-index existing files in github_path to update ChromaDB vector database only.

        This reads the already-indexed files from data/github/ and updates the
        ChromaDB collection with their embeddings. Does NOT clone repositories.
        """
        try:
            # Get all files in github_path
            extensions = {"py", "md", "yml", "yaml", "json", "toml"}
            file_contents = {}  # Store content: [(relative_path, text), ...]

            for repo_dir in self.github_path.iterdir():
                if repo_dir.is_dir():
                    for ext in extensions:
                        files = list(repo_dir.rglob(f"*.{ext}"))
                        for file_path in files:
                            try:
                                relative_path = str(
                                    file_path.relative_to(self.github_path)
                                )
                                text = file_path.read_text(
                                    encoding="utf-8", errors="ignore"
                                )
                                if text.strip():  # Only store non-empty files
                                    file_contents[(repo_dir.name, relative_path)] = text
                            except Exception as e:
                                print(f"Error reading {file_path}: {e}")

            if not file_contents:
                print("No content found to index in github_path")
                return False

            # Get all texts to process
            texts_list = []
            for (repo_name, relative_path), text in sorted(file_contents.items()):
                chunks = self._chunk_text(text, 1000, 200)
                for chunk in chunks:
                    if chunk.strip():
                        texts_list.append(chunk)

            print(
                f"Processing {len(texts_list)} chunks from {len(file_contents)} files..."
            )

            # Load embedding model using sentence-transformers from HuggingFace repo
            try:

                from sentence_transformers import SentenceTransformer

                # Use HuggingFace repo ID - sentence-transformers will cache locally
                model_id = "sentence-transformers/all-MiniLM-L6-v2"

                embedding_model = SentenceTransformer(model_id)
                print(f"Loaded embedding model: {model_id}")
            except Exception as e:
                print(f"Error loading model from HuggingFace: {e}")
                return False

            # Generate all embeddings at once (more efficient)
            print("Generating embeddings...")
            embeddings = embedding_model.encode(
                texts_list, convert_to_numpy=True, normalize_embeddings=True
            )

            # Set up ChromaDB client and collection
            try:
                from chromadb import PersistentClient

                client = PersistentClient(path=str(self.chroma_db_path))

                # Clear existing collection
                if client.list_collections():
                    client.delete_collection(name="documents")
                    print("Deleted existing collection 'documents'")

                # Create new collection
                embedding_service_collection = client.get_or_create_collection(
                    name="documents", metadata={"hnsw:space": "cosine"}
                )
            except Exception as e:
                print(f"Error managing ChromaDB collection: {e}")
                return False

            # Prepare data for insertion
            ids = []
            metadatas = []

            index = 0
            for (repo_name, relative_path), text in sorted(file_contents.items()):
                chunks = self._chunk_text(text, 1000, 200)
                for chunk in chunks:
                    if not chunk.strip():
                        continue

                    chunk_id = f"{repo_name}_{relative_path}_chunk_{index}"

                    ids.append(chunk_id)
                    metadatas.append(
                        {
                            "repository": repo_name,
                            "path": relative_path,
                            "index": index,
                        }
                    )
                    index += 1

            # Add to ChromaDB collection
            if ids:
                print(f"Adding {len(ids)} chunks to vector DB...")
                embedding_service_collection.add(
                    ids=ids,
                    embeddings=embeddings.tolist(),
                    documents=texts_list,
                    metadatas=metadatas,
                )
                print(f"Successfully indexed {len(ids)} chunks")

            return True

        except Exception as e:
            print(f"Reindex error: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _chunk_text(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> list[str]:
        """Split text into overlapping chunks."""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start = end - overlap if end < len(text) else len(text)

        return chunks

    def clear_context(self) -> bool:
        """Clear the RAG context."""
        try:
            return True
        except Exception as e:
            print(f"Clear context failed: {e}")
            return False
