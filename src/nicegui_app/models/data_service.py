# Data Service for NiceGUI with RAG capabilities
import logging
from typing import Optional, Dict, Any, List, Tuple
import os
import tempfile
import hashlib
from datetime import datetime
import time

# Import GitPython for repository operations
try:
    from git import Repo
    GITPYTHON_AVAILABLE = True
except ImportError as e:
    print(f"Warning: GitPython not available: {e}")
    GITPYTHON_AVAILABLE = False

# Import RAG components
try:
    import chromadb
    from chromadb.utils import embedding_functions
    import numpy as np
    
    # Store imports for later use
    CHROMADB_AVAILABLE = True
except ImportError as e:
    print(f"Warning: ChromaDB dependencies not available: {e}")
    CHROMADB_AVAILABLE = False

# Import ollama-python for embeddings
try:
    from ollama import Client
    OLLAMA_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Ollama not available: {e}")
    OLLAMA_AVAILABLE = False


class DataService:
    """
    A service to handle data operations with Retrieval-Augmented Generation (RAG) capabilities.
    
    Methods:
        - get_data: Retrieve data from a source.
        - save_data: Save data to a destination.
        - generate_embeddings: Create embeddings for text
        - store_context: Store document context in vector database
        - retrieve_context: Retrieve relevant context using similarity search
    """

    def __init__(self, embedding_model_name: str = 'all-MiniLM-L6-v2'):
        self.logger = logging.getLogger(__name__)
        self.embedding_model_name = embedding_model_name
        self.ollama_client: Optional[Client] = None  # type: ignore[name-defined]
        self.chroma_client: Optional[Any] = None
        self.collection: Optional[Any] = None
        
        # Initialize RAG components
        self._initialize_rag()

    def _ollama_with_retry(self, func, max_retries=3) -> Any:
        """
        Execute an Ollama API call with retry logic and exponential backoff.
        
        Args:
            func: The function to execute (e.g., self.ollama_client.generate)
            max_retries: Maximum number of retry attempts
            
        Returns:
            The result of the function call
            
        Raises:
            RuntimeError: If all retries fail
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    # Exponential backoff: 2^attempt seconds
                    wait_time = (2 ** attempt) * 0.5
                    self.logger.warning(
                        f"Attempt {attempt + 1} failed for Ollama call: {e}. "
                        f"Retrying in {wait_time:.1f}s..."
                    )
                    time.sleep(wait_time)
        
        error_msg = f"All {max_retries} attempts failed. Last error: {last_exception}"
        self.logger.error(error_msg)
        raise RuntimeError(error_msg)

    def _initialize_rag(self) -> None:
        """
        Initialize the embedding model and vector database.
        """
        try:
            # Initialize ollama client for embeddings
            if OLLAMA_AVAILABLE:
                from ollama import Client  # type: ignore[name-defined]
                self.ollama_client = Client(host='http://127.0.0.1:1234')
                self.logger.info(f"Initialized Ollama client at http://127.0.0.1:1234")
            else:
                self.logger.warning("Ollama not available. Embedding generation disabled.")
            
            # Initialize ChromaDB client only if available
            if CHROMADB_AVAILABLE:
                import chromadb  # type: ignore[name-defined]
                self.chroma_client = chromadb.PersistentClient(path=".chromadb")
                
                # Create or get collection for document context
                self.collection = self.chroma_client.get_or_create_collection(
                    name="document_context",
                    metadata={"hnsw:space": "cosine"}
                )
                self.logger.info("Initialized ChromaDB collection for document context")
            else:
                self.logger.warning("ChromaDB not available. RAG functionality disabled.")
            
        except ImportError as e:
            self.logger.warning(f"RAG components not available: {e}. Running in limited mode.")
        except Exception as e:
            self.logger.error(f"Error initializing RAG: {e}")
            raise

    def get_data(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data for the given key.
        
        Args:
            key (str): The key to retrieve data for.
            
        Returns:
            Optional[Dict[str, Any]]: The retrieved data or None if not found.
        """
        # Placeholder logic
        return {"key": key, "data": "sample_data"}

    def fetch_github_repositories(self, repo_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Fetch GitHub repositories based on the provided configuration.
        
        Args:
            repo_config (Dict[str, Any]): Configuration containing repository URLs and branches.
            
        Returns:
            List[Dict[str, Any]]: List of fetched repositories with metadata.
        """
        import requests
        from typing import Dict, Any, List
        
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
                parts = url.strip().split('/')
                if len(parts) < 5 or parts[2] != "github.com":
                    self.logger.warning(f"Invalid GitHub repository URL: {url}")
                    continue
                
                owner, repo_name = parts[3], parts[4]
                api_url = f"https://api.github.com/repos/{owner}/{repo_name}/contents?path=/&ref={branch}"
                
                # Fetch repository contents from GitHub API
                response = requests.get(api_url)
                if response.status_code == 200:
                    contents = response.json()
                    repositories.append({
                        "url": url,
                        "branch": branch,
                        "contents": contents,
                        "enabled": enabled,
                        "file_extensions": file_extensions
                    })
                else:
                    self.logger.error(f"Failed to fetch repository {url}: HTTP {response.status_code}")
        except Exception as e:
            self.logger.error(f"Error fetching GitHub repositories: {e}")
        
        return repositories

    def clone_enabled_repositories(self, repo_config: Dict[str, Any]) -> bool:
        """
        Clone enabled repositories into /docs/github and update existing ones.
        
        Args:
            repo_config (Dict[str, Any]): Configuration containing repository URLs and branches.
            
        Returns:
            bool: True if cloning was successful, False otherwise.
        """
        from pathlib import Path
        
        if not GITPYTHON_AVAILABLE:
            self.logger.error("GitPython not available")
            return False
        
        try:
            docs_github_dir = Path("docs/github")
            docs_github_dir.mkdir(parents=True, exist_ok=True)
            
            success_count = 0
            total_repos = sum(1 for repo in repo_config.get("repositories", []) 
                             if repo.get("enabled", False))
            
            for repo in repo_config.get("repositories", []):
                if not repo.get("enabled", False):
                    continue
                
                url = repo.get("url")
                branch = repo.get("branch", "main")
                
                if not url:
                    self.logger.warning(f"Repository missing URL, skipping")
                    continue
                
                # Extract owner and repo name from URL (e.g., https://github.com/user/repo)
                parts = url.strip().split('/')
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
                        repo_obj = Repo.clone_from(f"https://github.com/{owner}/{repo_name}.git", str(repo_dir))
                        repo_obj.git.checkout(branch)
                    
                    success_count += 1
                except Exception as e:
                    self.logger.error(f"Failed to process repository {repo_name}: {e}")
                    continue
            
            if success_count > 0:
                self.logger.info(f"Repository update completed. Successfully processed {success_count}/{total_repos} enabled repositories.")
                return True
            else:
                self.logger.warning("No enabled repositories were successfully updated.")
                return False
        except Exception as e:
            self.logger.error(f"Error cloning or updating repositories: {e}")
            return False

    def save_data(self, key: str, data: Dict[str, Any]) -> bool:
        """
        Save the given data for the specified key.
        
        Args:
            key (str): The key to save data under.
            data (Dict[str, Any]): The data to save.
            
        Returns:
            bool: True if data was saved successfully, False otherwise.
        """
        # Placeholder logic
        return True

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text strings using Ollama.
        
        Args:
            texts (List[str]): List of text strings to embed
            
        Returns:
            List[List[float]]: List of embedding vectors
            
        Raises:
            RuntimeError: If embedding service is not available or fails
        """
        if self.ollama_client is None:
            raise RuntimeError("Ollama client not initialized")
        
        if not texts:
            return []
        
        try:
            # Use Ollama to generate embeddings with retry logic
            def call_ollama():
                response = self.ollama_client.embed(
                    model='all-minilm',  # Using all-minilm-l6-v2 equivalent
                    input=texts,
                    options={'temperature': 0}
                )
                return response
            
            response = self._ollama_with_retry(call_ollama)
            
            # Extract embeddings from response
            if hasattr(response, 'embeddings'):
                embeddings = response.embeddings
            elif isinstance(response, dict) and 'embeddings' in response:
                embeddings = response['embeddings']
            else:
                self.logger.warning("Unexpected response format from Ollama embed API")
                # Fallback: create placeholder embeddings
                embedding_size = 384  # Default size for all-MiniLM-L6-v2
                if hasattr(response, 'embedding'):
                    embedding_size = len(response.embedding)
                elif isinstance(response, dict) and 'embedding' in response:
                    embedding_size = len(response['embedding'])
                
                embeddings = [[0.1] * embedding_size for _ in texts]
            
            return embeddings
        except Exception as e:
            self.logger.error(f"Error generating embeddings with Ollama: {e}")
            raise RuntimeError(f"Failed to generate embeddings: {str(e)}")

    def store_context(
        self,
        document_id: str,
        text_content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store document context in the vector database.
        
        Args:
            document_id (str): Unique identifier for the document
            text_content (str): Text content to store and index
            metadata (Optional[Dict[str, Any]]): Additional metadata about the document
            
        Returns:
            bool: True if context was stored successfully
            
        Raises:
            RuntimeError: If vector database is initialized but operation fails
        """
        if self.collection is None:
            self.logger.warning("Vector database not available - skipping context storage")
            return False
        
        try:
            # Generate embedding for the text content
            chunks = self._chunk_text(text_content)
            embeddings = self.generate_embeddings(chunks)
            
            # Store each chunk with its embedding
            ids = [f"{document_id}_{i}" for i in range(len(chunks))]
            
            self.collection.add(
                ids=ids,
                documents=chunks,
                embeddings=embeddings,
                metadatas=[{"chunk_index": i, **metadata} | metadata if metadata else {"chunk_index": i} for i in range(len(chunks))]
            )
            
            self.logger.info(f"Stored {len(chunks)} chunks for document {document_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error storing context: {e}")
            raise

    def retrieve_context(
        self,
        query: str,
        n_results: int = 5,
        min_relevance_score: float = 0.3
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Retrieve relevant context using similarity search.
        
        Args:
            query (str): The search query
            n_results (int): Maximum number of results to return
            min_relevance_score (float): Minimum relevance score threshold
            
        Returns:
            Tuple[List[str], List[Dict[str, Any]]]:
                - List of relevant document chunks
                - List of metadata for each chunk
            
        Raises:
            RuntimeError: If vector database is initialized but operation fails
        """
        if self.collection is None:
            self.logger.warning("Vector database not available - returning empty results")
            return [], []
        
        try:
            # Generate embedding for the query
            query_embedding = self.generate_embeddings([query])[0]
            
            # Query the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results
            )
            
            documents = results['documents'][0] if results['documents'] else []
            metadatas = results['metadatas'][0] if results['metadatas'] else []
            distances = results['distances'][0] if results['distances'] else []
            
            # Filter by minimum relevance score
            filtered_docs = []
            filtered_meta = []
            
            for doc, meta, dist in zip(documents, metadatas, distances):
                # Convert distance to similarity score (cosine distance -> similarity)
                # Distance of 0 = perfect match, 2 = opposite
                # We'll use a simple transformation: similarity = 1 - (distance / 2)
                similarity_score = 1 - (dist / 2) if dist <= 2 else 0
                
                if similarity_score >= min_relevance_score:
                    filtered_docs.append(doc)
                    # Add similarity score to metadata
                    meta_copy = meta.copy()
                    meta_copy['similarity_score'] = round(similarity_score, 3)
                    filtered_meta.append(meta_copy)
            
            self.logger.info(f"Retrieved {len(filtered_docs)} relevant chunks for query: {query[:50]}...")
            return filtered_docs, filtered_meta
            
        except Exception as e:
            self.logger.error(f"Error retrieving context: {e}")
            raise

    def _chunk_text(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        """
        Split text into overlapping chunks for better retrieval.
        
        Args:
            text (str): Input text to chunk
            chunk_size (int): Size of each chunk in characters
            overlap (int): Overlap between chunks in characters
            
        Returns:
            List[str]: List of text chunks
        """
        if not text or len(text) == 0:
            return [text]
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = end - overlap
        
        return chunks

    def clear_context(self) -> bool:
        """
        Clear all stored context from the vector database.
        
        Returns:
            bool: True if context was cleared successfully
        """
        try:
            if self.collection is not None:
                # Delete all documents from collection
                self.collection.delete(where={})
                self.logger.info("Cleared all document context")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing context: {e}")
            raise

    def get_context_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the stored context.
        
        Returns:
            Dict[str, Any]: Statistics including count and size
        """
        stats = {"count": 0, "size_mb": 0.0}
        
        try:
            if self.collection is not None:
                # Get collection metadata
                collection_metadata = self.chroma_client.get_collection(
                    name=self.collection.name,
                    heading=""
                )
                
                stats["count"] = collection_metadata.count
                stats["size_mb"] = round(collection_metadata.size / (1024 * 1024), 2)
            
        except Exception as e:
            self.logger.warning(f"Error getting context stats: {e}")
        
        return stats