"""
RAG Service for SigmaHQ RAG application.

Provides Retrieval-Augmented Generation functionality with ChromaDB integration,
optimized for performance and ease of use. Integrates with the new service architecture.
"""

import asyncio
import hashlib
import logging
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from datetime import datetime
from typing import Any

try:
    import chromadb
    from chromadb.config import Settings
    from chromadb.utils import embedding_functions
except ImportError as e:
    chromadb = None
    embedding_functions = None
    logging.warning(f"chromadb not available: {e}. RAG functionality disabled.")

from ..shared import (
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_RAG_PERSIST_DIRECTORY,
    SERVICE_RAG,
    STATUS_DEGRADED,
    STATUS_HEALTHY,
    STATUS_UNHEALTHY,
    AsyncComponent,
    BaseService,
    CacheService,
    DatabaseConfig,
    DatabaseError,
    EmbeddingConfig,
    LLMError,
    NetworkError,
    RAGError,
    get_cpu_usage,
    get_memory_usage,
    handle_service_errors,
    rate_limit,
    retry_with_backoff,
)
from .llm_service import LLMService


@dataclass
class RAGStats:
    """Statistics for RAG service."""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    total_documents: int = 0
    total_chunks: int = 0
    average_similarity_score: float = 0.0
    average_retrieval_time: float = 0.0
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0
    last_error: str | None = None
    uptime_seconds: float = 0.0


class RAGService(BaseService, AsyncComponent):
    """
    RAG service for SigmaHQ RAG application.
    
    Provides optimized RAG functionality with:
    - Direct ChromaDB integration
    - Better error handling and fallback mechanisms
    - Integration with optimized LLM service
    - Performance optimizations for real-time applications
    - Simplified API for common RAG operations
    - Comprehensive caching
    """

    def __init__(
        self,
        llm_service: LLMService | None = None,
        config: EmbeddingConfig | None = None,
        database_config: DatabaseConfig | None = None,
    ):
        """
        Initialize the RAG service.
        
        Args:
            llm_service: Pre-configured LLM service
            config: RAG configuration
            database_config: Database configuration
        """
        BaseService.__init__(self, f"{SERVICE_RAG}.rag_service")
        AsyncComponent.__init__(self)
        
        # Configuration
        self.config = config or self._get_default_config()
        self.database_config = database_config or self._get_default_database_config()
        
        # Services
        self.llm_service = llm_service
        self.local_embedding_service = None
        
        # Service state
        self.client = None
        self.collection = None
        self._initialized = False
        self._start_time = datetime.now()
        
        # Statistics
        self.stats = RAGStats()
        
        # Caching
        self.cache = CacheService(
            max_size=1000,
            default_ttl=3600
        )
        
        # Initialize RAG components
        self._initialize_rag()
        self._initialize_local_embedding_service()

    def _initialize_local_embedding_service(self) -> None:
        """Initialize the local embedding service with CPU-only configuration."""
        try:
            from .local_embedding_service import LocalEmbeddingService
            
            # Ensure CPU-only configuration for embeddings
            cpu_config = self.config.copy() if hasattr(self.config, 'copy') else dict(self.config)
            cpu_config['model'] = "all-MiniLM-L6-v2"  # Use sentence-transformers model
            
            self.local_embedding_service = LocalEmbeddingService(config=cpu_config)
            self.logger.info("Local CPU-only embedding service initialized")
        except Exception as e:
            self.logger.warning(f"Failed to initialize local embedding service: {e}")
            self.local_embedding_service = None

    def _get_default_config(self) -> EmbeddingConfig:
        """Get default RAG configuration."""
        return EmbeddingConfig(
            model=DEFAULT_EMBEDDING_MODEL,
            base_url="http://localhost:1234",
            api_key="lm-studio",
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP,
        )

    def _get_default_database_config(self) -> DatabaseConfig:
        """Get default database configuration."""
        return DatabaseConfig(
            path=DEFAULT_RAG_PERSIST_DIRECTORY,
            max_connections=5,
            timeout=30,
        )

    async def initialize(self) -> bool:
        """
        Initialize the RAG service.
        
        Returns:
            True if initialization successful, False otherwise
        """
        if self._initialized:
            return True
            
        try:
            success = self._initialize_rag()
            if success:
                self._initialized = True
                self._log_operation("RAG service initialization", True)
                self.logger.info(f"RAG service initialized with collection: {self.config['collection_name']}")
            else:
                self._log_operation("RAG service initialization", False)
                self.logger.error("RAG service initialization failed")
            
            return success
        except Exception as e:
            self._log_operation("RAG service initialization", False, {"error": str(e)})
            self.logger.error(f"RAG service initialization failed: {e}")
            return False

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.executor:
                self.executor.shutdown(wait=True)
                self.executor = None

            self._initialized = False
            self._log_operation("RAG service cleanup", True)
            
        except Exception as e:
            self._log_operation("RAG service cleanup", False, {"error": str(e)})
            self.logger.error(f"Error during RAG service cleanup: {e}")

    def _initialize_rag(self) -> bool:
        """Initialize the ChromaDB vector store."""
        if chromadb is None:
            self.logger.warning("ChromaDB not available. RAG functionality disabled.")
            return False

        try:
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(path=self.database_config['path'])

            # Create or get collection with custom embedding function
            self.collection = self.client.get_or_create_collection(
                name=self.config['collection_name'],
                metadata={"description": "RAG vector store for document retrieval"},
            )

            self.logger.info(
                f"Initialized ChromaDB at {self.database_config['path']} "
                f"with collection '{self.config['collection_name']}'"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error initializing RAG: {e}")
            return False

    def _generate_embeddings_sync(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings synchronously using LM Studio API."""
        if not texts:
            return []

        try:
            import requests

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.config['api_key']}",
            }

            # LM Studio expects the input as a string or array of strings
            payload = {"model": self.config['model'], "input": texts}

            response = requests.post(
                f"{self.config['base_url']}/v1/embeddings",
                headers=headers,
                json=payload,
                timeout=10,  # Reduced timeout to 10 seconds
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

        except requests.exceptions.ConnectionError as e:
            self.logger.warning(f"Connection error generating embeddings: {e}")
            # Return empty embeddings instead of raising error to prevent disconnection
            return [[] for _ in texts]
        except requests.exceptions.Timeout as e:
            self.logger.warning(f"Timeout generating embeddings: {e}")
            # Return empty embeddings instead of raising error to prevent disconnection
            return [[] for _ in texts]
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Request error generating embeddings: {e}")
            # Return empty embeddings instead of raising error to prevent disconnection
            return [[] for _ in texts]
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {e}")
            # Return empty embeddings instead of raising error to prevent disconnection
            return [[] for _ in texts]

    @handle_service_errors(error_types=[NetworkError, RAGError], default_message="Embedding generation failed")
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    @rate_limit(max_calls=50, time_window=60)  # 50 calls per minute
    async def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of text strings with fallback mechanism.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        try:
            # Try local embeddings first
            if self.local_embedding_service:
                try:
                    embeddings = await self.local_embedding_service.generate_embeddings(texts)
                    self.logger.info(f"Generated {len(texts)} embeddings using local service")
                    return embeddings
                except Exception as e:
                    self.logger.warning(f"Local embedding failed, falling back to API: {e}")
            
            # Fallback to LM Studio API
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                self.executor, self._generate_embeddings_sync, texts
            )
            return embeddings
            
        except Exception as e:
            self.logger.error(f"Error generating embeddings: {e}")
            raise RAGError(f"Failed to generate embeddings: {str(e)}")

    @handle_service_errors(error_types=[DatabaseError, RAGError], default_message="Context storage failed")
    async def store_context(
        self,
        document_id: str,
        text_content: str,
        metadata: dict[str, Any] | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
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
            actual_chunk_size = chunk_size or self.config['chunk_size']
            actual_chunk_overlap = chunk_overlap or self.config['chunk_overlap']

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
                    embeddings = loop.run_until_complete(
                        self.generate_embeddings(chunks)
                    )
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
                    **(metadata or {}),
                }
                for i, chunk in enumerate(chunks)
            ]

            # Add to collection
            self.collection.add(
                ids=ids, embeddings=embeddings, metadatas=metadatas, documents=chunks
            )

            # Update statistics
            self.stats.total_documents += 1
            self.stats.total_chunks += len(chunks)
            self._update_stats()

            self.logger.info(
                f"Stored {len(chunks)} chunks for document {document_id} "
                f"(chunk size: {actual_chunk_size}, overlap: {actual_chunk_overlap})"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error storing context for document {document_id}: {e}")
            return False

    @handle_service_errors(error_types=[DatabaseError, RAGError], default_message="Context retrieval failed")
    @retry_with_backoff(max_retries=3, base_delay=1.0, max_delay=10.0)
    @rate_limit(max_calls=100, time_window=60)  # 100 calls per minute
    async def retrieve_context(
        self,
        query: str,
        n_results: int = 5,
        min_relevance_score: float = 0.3,
        filter_metadata: dict[str, Any] | None = None,
    ) -> tuple[list[str], list[dict[str, Any]]]:
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
            # Check cache first
            cache_key = self._generate_cache_key("retrieve_context", query, n_results, min_relevance_score, filter_metadata)
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                self.stats.total_queries += 1
                self.stats.successful_queries += 1
                self._update_stats()
                self.logger.info("Context retrieval served from cache")
                return cached_result

            # Generate embedding for query
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # If we're already in an event loop, use sync method
                    query_embedding = self._generate_embeddings_sync([query])[0]
                else:
                    query_embedding = loop.run_until_complete(
                        self.generate_embeddings([query])
                    )[0]
            except RuntimeError:
                # No event loop available, use sync method
                query_embedding = self._generate_embeddings_sync([query])[0]

            # Query the collection
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"],
            )

            if not results["documents"] or not results["documents"][0]:
                return [], []

            documents = results["documents"][0]
            metadatas = results["metadatas"][0] if results["metadatas"] else [{}]
            distances = results["distances"][0] if results["distances"] else [1.0]

            # Filter by minimum relevance score and convert to similarity
            filtered_docs = []
            filtered_meta = []
            total_similarity = 0.0

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
                    total_similarity += similarity_score

            # Cache the result
            result = (filtered_docs, filtered_meta)
            await self.cache.set(cache_key, result, ttl=1800)  # 30 minutes

            # Update statistics
            self.stats.total_queries += 1
            self.stats.successful_queries += 1
            if filtered_docs:
                avg_similarity = total_similarity / len(filtered_docs)
                self.stats.average_similarity_score = (
                    (self.stats.average_similarity_score * (self.stats.successful_queries - 1)) + avg_similarity
                ) / self.stats.successful_queries
            self._update_stats()

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
    ) -> list[str]:
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

    @handle_service_errors(error_types=[DatabaseError, RAGError], default_message="Context clearing failed")
    async def clear_context(self) -> bool:
        """Clear all stored context from the vector database."""
        try:
            if self.collection is not None:
                # Delete all documents from collection
                self.collection.delete(where={})
                self.stats.total_documents = 0
                self.stats.total_chunks = 0
                self._update_stats()
                self.logger.info("Cleared all document context")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing context: {e}")
            return False

    def get_context_stats(self) -> dict[str, Any]:
        """Get statistics about the stored context."""
        stats = {
            "count": 0,
            "embedding_model": self.config['model'],
            "persist_directory": self.database_config['path'],
            "collection_name": self.config['collection_name'],
        }

        try:
            if self.collection is not None:
                # Get collection count
                collection_stats = self.collection.count()
                stats["count"] = collection_stats
                
                # Calculate approximate size
                try:
                    import os
                    if os.path.exists(self.database_config['path']):
                        total_size = 0
                        for dirpath, dirnames, filenames in os.walk(self.database_config['path']):
                            for f in filenames:
                                fp = os.path.join(dirpath, f)
                                total_size += os.path.getsize(fp)
                        stats["size_mb"] = round(total_size / (1024 * 1024), 2)
                    else:
                        stats["size_mb"] = 0
                except Exception as size_error:
                    self.logger.warning(f"Could not calculate database size: {size_error}")
                    stats["size_mb"] = 0

                # Add chunking configuration
                stats["default_chunk_size"] = self.config['chunk_size']
                stats["default_chunk_overlap"] = self.config['chunk_overlap']

        except Exception as e:
            self.logger.error(f"Error getting context stats: {e}")
            # Return basic stats even if there's an error
            stats["error"] = str(e)

        return stats

    def update_chunking_config(self, chunk_size: int, chunk_overlap: int) -> None:
        """Update the default chunking configuration."""
        self.config['chunk_size'] = chunk_size
        self.config['chunk_overlap'] = chunk_overlap
        self.logger.info(
            f"Updated chunking config: size={chunk_size}, overlap={chunk_overlap}"
        )

    def _get_cache_key(self, texts: list[str]) -> str:
        """Generate a cache key for a list of texts."""
        text_hash = hashlib.md5("||".join(texts).encode()).hexdigest()
        return f"embeddings_{self.config['model']}_{text_hash}"

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache entry is valid (not expired)."""
        if cache_key not in self._cache:
            return False

        cached_data, timestamp = self._cache[cache_key]
        current_time = time.time()

        # Check if cache has expired
        if current_time - timestamp > self.cache.default_ttl:
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
            if current_time - timestamp > self.cache.default_ttl:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]
            del self._cache_access_times[key]

        # Enforce cache size limit using LRU
        if len(self._cache) > self.cache.max_size:
            # Sort by access time and remove oldest entries
            sorted_keys = sorted(self._cache_access_times.items(), key=lambda x: x[1])
            keys_to_remove = len(self._cache) - self.cache.max_size

            for key, _ in sorted_keys[:keys_to_remove]:
                del self._cache[key]
                del self._cache_access_times[key]

    def generate_embeddings_cached(self, texts: list[str]) -> list[list[float]]:
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
        filter_metadata: dict[str, Any] | None = None,
    ) -> tuple[list[str], list[dict[str, Any]]]:
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
        self.cache.clear()
        self.logger.info("Cleared all cached data")

    def get_cache_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        current_time = time.time()
        valid_entries = sum(
            1
            for _, timestamp in self._cache.values()
            if current_time - timestamp <= self.cache.default_ttl
        )

        return {
            "total_entries": len(self._cache),
            "valid_entries": valid_entries,
            "expired_entries": len(self._cache) - valid_entries,
            "cache_size_limit": self.cache.max_size,
            "cache_ttl": self.cache.default_ttl,
        }

    @handle_service_errors(error_types=[RAGError, LLMError], default_message="RAG response generation failed")
    async def generate_rag_response(
        self,
        query: str,
        system_prompt: str | None = None,
        n_results: int = 3,
        min_relevance_score: float = 0.1,
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
            relevant_docs, metadata = await self.retrieve_context(
                query=query,
                n_results=n_results,
                min_relevance_score=min_relevance_score,
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
            if self.llm_service:
                response = await self.llm_service.simple_completion(
                    prompt=enhanced_prompt, system_prompt=system_prompt
                )
            else:
                # Fallback to simple completion
                response = "Error: LLM service not available for RAG response generation"

            return response

        except Exception as e:
            self.logger.error(f"Error generating RAG response: {e}")
            # Fallback to simple completion
            return f"Error: {str(e)}"

    @handle_service_errors(error_types=[RAGError, LLMError], default_message="RAG streaming response generation failed")
    async def generate_streaming_rag_response(
        self,
        query: str,
        system_prompt: str | None = None,
        n_results: int = 3,
        min_relevance_score: float = 0.1,
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
            # Retrieve relevant context with timeout
            try:
                import asyncio
                context_task = asyncio.create_task(
                    self.retrieve_context(
                        query=query,
                        n_results=n_results,
                        min_relevance_score=min_relevance_score,
                    )
                )
                # Set timeout for RAG operations (25 seconds)
                relevant_docs, metadata = await asyncio.wait_for(context_task, timeout=25.0)
            except asyncio.TimeoutError:
                self.logger.warning("RAG context retrieval timed out, using original query")
                relevant_docs = []
                metadata = []
            except Exception as context_error:
                self.logger.error(f"RAG context retrieval failed: {context_error}, using original query")
                relevant_docs = []
                metadata = []

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
            if self.llm_service:
                try:
                    response_generator = self.llm_service.streaming_completion(
                        prompt=enhanced_prompt, system_prompt=system_prompt
                    )
                    
                    # Check if it's an async generator
                    if hasattr(response_generator, '__aiter__'):
                        # It's an async generator, use async for
                        async for chunk in response_generator:
                            yield chunk
                    elif asyncio.iscoroutine(response_generator):
                        # It's a coroutine, await it and yield the result
                        response = await response_generator
                        yield response
                    else:
                        # Unknown type, handle gracefully
                        self.logger.error(f"Unknown response type from LLM service: {type(response_generator)}")
                        yield "Error: Invalid response type from LLM service"
                except Exception as llm_error:
                    self.logger.error(f"LLM streaming failed: {llm_error}, falling back to simple completion")
                    # Fallback to simple completion
                    try:
                        response = await self.llm_service.simple_completion(
                            prompt=enhanced_prompt, system_prompt=system_prompt
                        )
                        yield response
                    except Exception as fallback_error:
                        yield f"Error: {str(fallback_error)}"
            else:
                # Fallback to simple streaming completion
                yield "Error: LLM service not available for RAG streaming response generation"

        except Exception as e:
            self.logger.error(f"Error generating streaming RAG response: {e}")
            # Fallback to simple streaming completion
            yield f"Error: {str(e)}"

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

    def _update_stats(self) -> None:
        """Update service statistics."""
        # Update memory and CPU usage
        memory_info = get_memory_usage()
        self.stats.memory_usage_mb = memory_info.get("rss_mb", 0)
        self.stats.cpu_usage_percent = get_cpu_usage()
        
        # Update uptime
        self.stats.uptime_seconds = (datetime.now() - self._start_time).total_seconds()

    def get_health_status(self) -> dict[str, Any]:
        """Get service health status."""
        status = STATUS_HEALTHY
        issues = []
        
        # Check client availability
        if self.client is None:
            status = STATUS_UNHEALTHY
            issues.append("ChromaDB client not initialized")
        
        # Check collection availability
        if self.collection is None:
            status = STATUS_UNHEALTHY
            issues.append("Collection not available")
        
        # Check error rate
        if self.stats.total_queries > 0:
            error_rate = self.stats.failed_queries / self.stats.total_queries
            if error_rate > 0.1:  # More than 10% error rate
                status = STATUS_DEGRADED
                issues.append(f"High error rate: {error_rate:.2%}")
        
        # Check response time
        if self.stats.average_retrieval_time > 10.0:  # More than 10 seconds average
            status = STATUS_DEGRADED
            issues.append(f"High retrieval time: {self.stats.average_retrieval_time:.2f}s")
        
        # Check memory usage
        if self.stats.memory_usage_mb > 1024.0:  # More than 1GB
            status = STATUS_DEGRADED
            issues.append(f"High memory usage: {self.stats.memory_usage_mb:.2f}MB")
        
        return {
            "service": SERVICE_RAG,
            "status": status,
            "issues": issues,
            "timestamp": datetime.now().isoformat(),
            "stats": {
                "total_queries": self.stats.total_queries,
                "successful_queries": self.stats.successful_queries,
                "failed_queries": self.stats.failed_queries,
                "total_documents": self.stats.total_documents,
                "total_chunks": self.stats.total_chunks,
                "average_similarity_score": self.stats.average_similarity_score,
                "average_retrieval_time": self.stats.average_retrieval_time,
                "memory_usage_mb": self.stats.memory_usage_mb,
                "cpu_usage_percent": self.stats.cpu_usage_percent,
                "last_error": self.stats.last_error,
                "uptime_seconds": self.stats.uptime_seconds,
            },
            "context_stats": self.get_context_stats(),
            "cache_stats": self.get_cache_stats(),
        }

    def get_usage_stats(self) -> dict[str, Any]:
        """Get comprehensive usage statistics."""
        return {
            "config": self.config,
            "database_config": self.database_config,
            "service_stats": {
                "total_queries": self.stats.total_queries,
                "successful_queries": self.stats.successful_queries,
                "failed_queries": self.stats.failed_queries,
                "total_documents": self.stats.total_documents,
                "total_chunks": self.stats.total_chunks,
                "average_similarity_score": self.stats.average_similarity_score,
                "average_retrieval_time": self.stats.average_retrieval_time,
                "memory_usage_mb": self.stats.memory_usage_mb,
                "cpu_usage_percent": self.stats.cpu_usage_percent,
                "last_error": self.stats.last_error,
                "uptime_seconds": self.stats.uptime_seconds,
            },
            "context_stats": self.get_context_stats(),
            "cache_stats": self.get_cache_stats(),
        }

    def update_config(self, new_config: EmbeddingConfig) -> bool:
        """Update RAG configuration."""
        try:
            self.config = new_config
            self.logger.info(f"RAG configuration updated: {new_config['model']}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update RAG configuration: {e}")
            return False


# Convenience factory functions for common RAG configurations
def create_rag_service(
    llm_service: LLMService | None = None,
    config: EmbeddingConfig | None = None,
    database_config: DatabaseConfig | None = None,
) -> RAGService:
    """Create a general-purpose RAG service."""
    default_config = EmbeddingConfig(
        model=DEFAULT_EMBEDDING_MODEL,
        base_url="http://localhost:1234",
        api_key="lm-studio",
        chunk_size=DEFAULT_CHUNK_SIZE,
        chunk_overlap=DEFAULT_CHUNK_OVERLAP,
    )
    
    default_database_config = DatabaseConfig(
        path=DEFAULT_RAG_PERSIST_DIRECTORY,
        max_connections=5,
        timeout=30,
    )
    
    if config:
        default_config.update(config)
    if database_config:
        default_database_config.update(database_config)
    
    return RAGService(
        llm_service=llm_service,
        config=default_config,
        database_config=default_database_config,
    )


def create_document_rag_service(
    llm_service: LLMService | None = None,
    database_config: DatabaseConfig | None = None,
) -> RAGService:
    """Create a RAG service optimized for document processing."""
    default_config = EmbeddingConfig(
        model=DEFAULT_EMBEDDING_MODEL,
        base_url="http://localhost:1234",
        api_key="lm-studio",
        chunk_size=1000,  # Larger chunks for documents
        chunk_overlap=200,
    )
    
    default_database_config = DatabaseConfig(
        path=DEFAULT_RAG_PERSIST_DIRECTORY,
        max_connections=5,
        timeout=30,
    )
    
    if database_config:
        default_database_config.update(database_config)
    
    return RAGService(
        llm_service=llm_service,
        config=default_config,
        database_config=default_database_config,
    )


def create_chat_rag_service(
    llm_service: LLMService | None = None,
    database_config: DatabaseConfig | None = None,
) -> RAGService:
    """Create a RAG service optimized for chat applications."""
    default_config = EmbeddingConfig(
        model=DEFAULT_EMBEDDING_MODEL,
        base_url="http://localhost:1234",
        api_key="lm-studio",
        chunk_size=300,  # Smaller chunks for chat
        chunk_overlap=50,
    )
    
    default_database_config = DatabaseConfig(
        path=DEFAULT_RAG_PERSIST_DIRECTORY,
        max_connections=5,
        timeout=30,
    )
    
    if database_config:
        default_database_config.update(database_config)
    
    return RAGService(
        llm_service=llm_service,
        config=default_config,
        database_config=default_database_config,
    )


# Backward compatibility alias
OptimizedRAGService = RAGService