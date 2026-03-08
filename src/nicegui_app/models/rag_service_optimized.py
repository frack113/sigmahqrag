"""
Optimized RAG Service for NiceGUI with ChromaDB integration

Handles Retrieval-Augmented Generation (RAG) operations using ChromaDB for vector storage
and the optimized LLM service for generation. Provides better performance, error handling,
and integration with the new LLM service architecture.
"""

import asyncio
import hashlib
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Tuple, AsyncGenerator

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
except ImportError as e:
    chromadb = None
    embedding_functions = None
    logging.warning(
        f"chromadb not available: {e}. RAG functionality disabled."
    )

from .llm_service_optimized import OptimizedLLMService


class OptimizedRAGService:
    """
    Optimized RAG service with ChromaDB integration.

    Key improvements:
    - Direct ChromaDB integration without LangChain overhead
    - Better error handling and fallback mechanisms
    - Integration with optimized LLM service
    - Performance optimizations for real-time applications
    - Simplified API for common RAG operations
    """

    def __init__(
        self,
        llm_service: Optional[OptimizedLLMService] = None,
        embedding_model_name: str = "text-embedding-all-minilm-l6-v2-embedding",
        base_url: str = "http://localhost:1234",
        persist_directory: str = ".chromadb",
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        api_key: str = "lm-studio",
        max_workers: int = 4,
        cache_size: int = 1000,
        cache_ttl: int = 3600,  # 1 hour
        collection_name: str = "rag_collection",
    ):
        """
        Initialize the optimized RAG service.

        Args:
            llm_service: Optional pre-configured LLM service
            embedding_model_name: Name of the embedding model to use
            base_url: Base URL for LM Studio server
            persist_directory: Directory to persist vector store
            chunk_size: Default size of each chunk in characters
            chunk_overlap: Default overlap between chunks in characters
            api_key: API key for LM Studio
            max_workers: Maximum number of worker threads
            cache_size: Maximum number of cached items
            cache_ttl: Cache time-to-live in seconds
            collection_name: Name of the ChromaDB collection
        """
        self.logger = logging.getLogger(__name__)
        self.embedding_model_name = embedding_model_name
        self.base_url = base_url
        self.persist_directory = persist_directory
        self.default_chunk_size = chunk_size
        self.default_chunk_overlap = chunk_overlap
        self.api_key = api_key
        self.max_workers = max_workers
        self.cache_size = cache_size
        self.cache_ttl = cache_ttl
        self.collection_name = collection_name

        # Initialize LLM service
        self.llm_service = llm_service or OptimizedLLMService(
            base_url=base_url,
            api_key=api_key,
            enable_streaming=True
        )

        # Initialize ChromaDB
        self.client = None
        self.collection = None
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        # Initialize caching
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_access_times: Dict[str, float] = {}

        # Initialize RAG components
        self._initialize_rag()

    def _initialize_rag(self) -> None:
        """Initialize the ChromaDB vector store."""
        if chromadb is None:
            self.logger.warning("ChromaDB not available. RAG functionality disabled.")
            return

        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(path=self.persist_directory)
            
            # Create or get collection with custom embedding function
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "RAG vector store for document retrieval"}
            )
            
            self.logger.info(
                f"Initialized ChromaDB at {self.persist_directory} "
                f"with collection '{self.collection_name}'"
            )

        except Exception as e:
            self.logger.error(f"Error initializing RAG: {e}")
            raise

    def _generate_embeddings_sync(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings synchronously using LM Studio API."""
        if not texts:
            return []

        try:
            import requests
            
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            
            # LM Studio expects the input as a string or array of strings
            payload = {"model": self.embedding_model_name, "input": texts}

            response = requests.post(
                f"{self.base_url}/v1/embeddings",
                headers=headers,
                json=payload,
                timeout=30,
            )

            response.raise_for_status()
            data = response.json()

            # Extract embeddings from the response
            embeddings = []
            for item in data.get("data", []):
                if "embedding" in item:
                    embeddings.append(item["embedding"])
                else:
                    self.logger.warning("No embedding found in response item")
                    embeddings.append([])

            self.logger.info(f"Generated embeddings for {len(texts)} texts")
            return embeddings

        except Exception as e:
            self.logger.error(f"Error generating embeddings: {e}")
            raise RuntimeError(f"Failed to generate embeddings: {str(e)}")

    async def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text strings.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                self.executor, self._generate_embeddings_sync, texts
            )
            return embeddings
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {e}")
            raise RuntimeError(f"Failed to generate embeddings: {str(e)}")

    def store_context(
        self,
        document_id: str,
        text_content: str,
        metadata: Optional[Dict[str, Any]] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
    ) -> bool:
        """
        Store document context in the vector database.

        Args:
            document_id: Unique identifier for the document
            text_content: Text content to store and index
            metadata: Additional metadata about the document
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters

        Returns:
            True if context was stored successfully
        """
        if self.collection is None:
            self.logger.warning(
                "Vector database not available - skipping context storage"
            )
            return False

        try:
            # Use provided chunking parameters or defaults
            actual_chunk_size = chunk_size or self.default_chunk_size
            actual_chunk_overlap = chunk_overlap or self.default_chunk_overlap

            # Generate chunks
            chunks = self._chunk_text(
                text_content, actual_chunk_size, actual_chunk_overlap
            )

            if not chunks:
                self.logger.warning(f"No chunks generated for document {document_id}")
                return False

            # Generate embeddings
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in an event loop, run in executor
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(self._generate_embeddings_sync, chunks)
                        embeddings = future.result()
                else:
                    embeddings = loop.run_until_complete(self.generate_embeddings(chunks))
            except RuntimeError:
                # No event loop available, use sync method
                embeddings = self._generate_embeddings_sync(chunks)

            # Prepare data for ChromaDB
            ids = [f"{document_id}_{i}" for i in range(len(chunks))]
            metadatas = [
                {
                    "document_id": document_id,
                    "chunk_index": i,
                    "chunk_size": len(chunk),
                    "source": "rag_service",
                    **(metadata or {})
                }
                for i, chunk in enumerate(chunks)
            ]

            # Add to collection
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=chunks
            )

            self.logger.info(
                f"Stored {len(chunks)} chunks for document {document_id} "
                f"(chunk size: {actual_chunk_size}, overlap: {actual_chunk_overlap})"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error storing context for document {document_id}: {e}")
            return False

    def retrieve_context(
        self,
        query: str,
        n_results: int = 5,
        min_relevance_score: float = 0.3,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Retrieve relevant context using similarity search.

        Args:
            query: The search query
            n_results: Maximum number of results to return
            min_relevance_score: Minimum relevance score threshold (0.0 to 1.0)
            filter_metadata: Optional metadata filter for more targeted search

        Returns:
            Tuple of (relevant document chunks, metadata for each chunk)
        """
        if self.collection is None:
            self.logger.warning(
                "Vector database not available - returning empty results"
            )
            return [], []

        try:
            # Generate embedding for query
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in an event loop, use sync method
                    query_embedding = self._generate_embeddings_sync([query])[0]
                else:
                    query_embedding = loop.run_until_complete(self.generate_embeddings([query]))[0]
            except RuntimeError:
                # No event loop available, use sync method
                query_embedding = self._generate_embeddings_sync([query])[0]

            # Query the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"]
            )

            if not results["documents"] or not results["documents"][0]:
                return [], []

            documents = results["documents"][0]
            metadatas = results["metadatas"][0] if results["metadatas"] else [{}]
            distances = results["distances"][0] if results["distances"] else [1.0]

            # Filter by minimum relevance score and convert to similarity
            filtered_docs = []
            filtered_meta = []

            for doc, meta, distance in zip(documents, metadatas, distances):
                # Convert distance to similarity score (0 to 1 scale)
                similarity_score = max(0, 1 - (distance / 2)) if distance <= 2 else 0

                if similarity_score >= min_relevance_score:
                    filtered_docs.append(doc)
                    # Add similarity score to metadata
                    meta_copy = meta.copy() if meta else {}
                    meta_copy["similarity_score"] = round(similarity_score, 3)
                    meta_copy["distance"] = round(distance, 3)
                    filtered_meta.append(meta_copy)

            self.logger.info(
                f"Retrieved {len(filtered_docs)} relevant chunks for query: "
                f"{query[:50]}... (threshold: {min_relevance_score})"
            )
            return filtered_docs, filtered_meta

        except Exception as e:
            self.logger.error(f"Error retrieving context: {e}")
            return [], []

    def _chunk_text(
        self, text: str, chunk_size: int = 1000, chunk_overlap: int = 200
    ) -> List[str]:
        """Split text into overlapping chunks for better retrieval."""
        if not text or len(text) == 0:
            return [""]

        chunks = []
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end]
            chunks.append(chunk)

            if end == len(text):
                break

            # Move start position with overlap
            start = end - chunk_overlap

        return chunks

    def clear_context(self) -> bool:
        """Clear all stored context from the vector database."""
        try:
            if self.collection is not None:
                # Delete all documents from collection
                self.collection.delete(where={})
                self.logger.info("Cleared all document context")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing context: {e}")
            return False

    def get_context_stats(self) -> Dict[str, Any]:
        """Get statistics about the stored context."""
        stats = {
            "count": 0,
            "embedding_model": self.embedding_model_name,
            "persist_directory": self.persist_directory,
            "collection_name": self.collection_name,
        }

        try:
            if self.collection is not None:
                collection_stats = self.collection.count()
                stats["count"] = collection_stats

                # Add chunking configuration
                stats["default_chunk_size"] = self.default_chunk_size
                stats["default_chunk_overlap"] = self.default_chunk_overlap

        except Exception as e:
            self.logger.warning(f"Error getting context stats: {e}")

        return stats

    def update_chunking_config(self, chunk_size: int, chunk_overlap: int) -> None:
        """Update the default chunking configuration."""
        self.default_chunk_size = chunk_size
        self.default_chunk_overlap = chunk_overlap
        self.logger.info(
            f"Updated chunking config: size={chunk_size}, overlap={chunk_overlap}"
        )

    def _get_cache_key(self, texts: List[str]) -> str:
        """Generate a cache key for a list of texts."""
        text_hash = hashlib.md5("||".join(texts).encode()).hexdigest()
        return f"embeddings_{self.embedding_model_name}_{text_hash}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid (not expired)."""
        if cache_key not in self._cache:
            return False

        cached_data, timestamp = self._cache[cache_key]
        current_time = time.time()

        # Check if cache has expired
        if current_time - timestamp > self.cache_ttl:
            del self._cache[cache_key]
            del self._cache_access_times[cache_key]
            return False

        return True

    def _cleanup_cache(self) -> None:
        """Remove expired cache entries and enforce cache size limit."""
        current_time = time.time()
        expired_keys = []

        # Remove expired entries
        for key, (cached_data, timestamp) in self._cache.items():
            if current_time - timestamp > self.cache_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]
            del self._cache_access_times[key]

        # Enforce cache size limit using LRU
        if len(self._cache) > self.cache_size:
            # Sort by access time and remove oldest entries
            sorted_keys = sorted(self._cache_access_times.items(), key=lambda x: x[1])
            keys_to_remove = len(self._cache) - self.cache_size

            for key, _ in sorted_keys[:keys_to_remove]:
                del self._cache[key]
                del self._cache_access_times[key]

    def generate_embeddings_cached(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings with caching for better performance."""
        if not texts:
            return []

        cache_key = self._get_cache_key(texts)

        # Check cache first
        if self._is_cache_valid(cache_key):
            self._cache_access_times[cache_key] = time.time()
            cached_embeddings, _ = self._cache[cache_key]
            self.logger.info(f"Cache hit for embeddings: {len(texts)} texts")
            return cached_embeddings

        # Generate new embeddings
        embeddings = asyncio.run(self.generate_embeddings(texts))

        # Cache the result
        self._cache[cache_key] = (embeddings, time.time())
        self._cache_access_times[cache_key] = time.time()

        # Cleanup cache if needed
        self._cleanup_cache()

        return embeddings

    def retrieve_context_cached(
        self,
        query: str,
        n_results: int = 5,
        min_relevance_score: float = 0.3,
        filter_metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Retrieve context with caching for better performance."""
        if not query.strip():
            return [], []

        # Create cache key based on query and parameters
        cache_params = {
            "query": query,
            "n_results": n_results,
            "min_relevance_score": min_relevance_score,
            "filter_metadata": filter_metadata or {},
        }
        cache_key = hashlib.md5(str(cache_params).encode()).hexdigest()

        # Check cache first
        if self._is_cache_valid(cache_key):
            self._cache_access_times[cache_key] = time.time()
            cached_result, _ = self._cache[cache_key]
            self.logger.info(f"Cache hit for context retrieval: {query[:50]}...")
            return cached_result

        # Perform actual retrieval
        result = self.retrieve_context(
            query, n_results, min_relevance_score, filter_metadata
        )

        # Cache the result
        self._cache[cache_key] = (result, time.time())
        self._cache_access_times[cache_key] = time.time()

        # Cleanup cache if needed
        self._cleanup_cache()

        return result

    def clear_cache(self) -> None:
        """Clear all cached data."""
        self._cache.clear()
        self._cache_access_times.clear()
        self.logger.info("Cleared all cached data")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        valid_entries = sum(
            1
            for _, timestamp in self._cache.values()
            if current_time - timestamp <= self.cache_ttl
        )

        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
            "cache_size_limit": self.cache_size,
            "cache_ttl": self.cache_ttl,
        }

    async def generate_rag_response(
        self, 
        query: str, 
        system_prompt: Optional[str] = None,
        n_results: int = 3,
        min_relevance_score: float = 0.1
    ) -> str:
        """
        Generate a RAG response by combining retrieval and generation.

        Args:
            query: The user's query
            system_prompt: Optional system prompt for the LLM
            n_results: Number of documents to retrieve
            min_relevance_score: Minimum similarity threshold

        Returns:
            Generated response text
        """
        try:
            # Retrieve relevant context from vector database
            relevant_docs, metadata = self.retrieve_context(
                query=query, 
                n_results=n_results, 
                min_relevance_score=min_relevance_score
            )

            # Build context string
            if relevant_docs:
                context_text = "\n\n".join(relevant_docs)
                # Limit context length to avoid token limits
                if len(context_text) > 4000:
                    context_text = context_text[:4000] + "..."
                
                # Create enhanced prompt with context
                enhanced_prompt = f"""Use the following context to answer the question:

Context:
{context_text}

Question: {query}

Answer concisely and accurately based on the provided context."""
            else:
                # No relevant context found, use original query
                enhanced_prompt = query

            # Generate response using LLM service
            response = self.llm_service.simple_completion(
                prompt=enhanced_prompt,
                system_prompt=system_prompt
            )

            return response

        except Exception as e:
            self.logger.error(f"Error generating RAG response: {e}")
            # Fallback to simple completion
            return self.llm_service.simple_completion(
                prompt=query,
                system_prompt=system_prompt or "You are a helpful assistant."
            )

    async def generate_streaming_rag_response(
        self, 
        query: str, 
        system_prompt: Optional[str] = None,
        n_results: int = 3,
        min_relevance_score: float = 0.1
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming RAG response.

        Args:
            query: The user's query
            system_prompt: Optional system prompt for the LLM
            n_results: Number of documents to retrieve
            min_relevance_score: Minimum similarity threshold

        Yields:
            Response chunks for streaming
        """
        try:
            # Retrieve relevant context
            relevant_docs, metadata = self.retrieve_context(
                query=query, 
                n_results=n_results, 
                min_relevance_score=min_relevance_score
            )

            # Build context string
            if relevant_docs:
                context_text = "\n\n".join(relevant_docs)
                # Limit context length to avoid token limits
                if len(context_text) > 4000:
                    context_text = context_text[:4000] + "..."
                
                # Create enhanced prompt with context
                enhanced_prompt = f"""Use the following context to answer the question:

Context:
{context_text}

Question: {query}

Answer concisely and accurately based on the provided context."""
            else:
                # No relevant context found, use original query
                enhanced_prompt = query

            # Generate streaming response using LLM service
            async for chunk in self.llm_service.streaming_completion(
                prompt=enhanced_prompt,
                system_prompt=system_prompt
            ):
                yield chunk

        except Exception as e:
            self.logger.error(f"Error generating streaming RAG response: {e}")
            # Fallback to simple streaming completion
            async for chunk in self.llm_service.streaming_completion(
                prompt=query,
                system_prompt=system_prompt or "You are a helpful assistant."
            ):
                yield chunk

    def check_availability(self) -> bool:
        """Check if the RAG service is available."""
        try:
            if self.collection is not None:
                # Try a simple count operation
                count = self.collection.count()
                return count >= 0
            return False
        except Exception as e:
            self.logger.error(f"RAG service availability check failed: {e}")
            return False

    def cleanup(self):
        """Clean up resources."""
        try:
            if self.executor:
                self.executor.shutdown(wait=True)
            self.clear_cache()
        except Exception as e:
            self.logger.error(f"Error during RAG service cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


# Convenience factory functions for common RAG configurations
def create_rag_service(
    llm_service: Optional[OptimizedLLMService] = None,
    embedding_model_name: str = "text-embedding-all-minilm-l6-v2-embedding",
    base_url: str = "http://localhost:1234",
    persist_directory: str = ".chromadb",
    chunk_size: int = 500,
    chunk_overlap: int = 100,
    collection_name: str = "rag_collection"
) -> OptimizedRAGService:
    """Create a general-purpose RAG service."""
    return OptimizedRAGService(
        llm_service=llm_service,
        embedding_model_name=embedding_model_name,
        base_url=base_url,
        persist_directory=persist_directory,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        collection_name=collection_name
    )


def create_document_rag_service(
    llm_service: Optional[OptimizedLLMService] = None,
    base_url: str = "http://localhost:1234",
    persist_directory: str = ".chromadb",
    collection_name: str = "documents"
) -> OptimizedRAGService:
    """Create a RAG service optimized for document processing."""
    return OptimizedRAGService(
        llm_service=llm_service,
        embedding_model_name="text-embedding-all-minilm-l6-v2-embedding",
        base_url=base_url,
        persist_directory=persist_directory,
        chunk_size=1000,  # Larger chunks for documents
        chunk_overlap=200,
        collection_name=collection_name
    )


def create_chat_rag_service(
    llm_service: Optional[OptimizedLLMService] = None,
    base_url: str = "http://localhost:1234",
    persist_directory: str = ".chromadb",
    collection_name: str = "chat_context"
) -> OptimizedRAGService:
    """Create a RAG service optimized for chat applications."""
    return OptimizedRAGService(
        llm_service=llm_service,
        embedding_model_name="text-embedding-all-minilm-l6-v2-embedding",
        base_url=base_url,
        persist_directory=persist_directory,
        chunk_size=300,   # Smaller chunks for chat
        chunk_overlap=50,
        collection_name=collection_name
    )


# Backward compatibility alias
RAGService = OptimizedRAGService