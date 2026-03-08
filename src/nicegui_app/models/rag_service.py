"""
RAG Service for NiceGUI with LangChain integration

Handles Retrieval-Augmented Generation (RAG) operations using LangChain's OpenAI-compatible embedding models and vector stores.
Optimized for better performance and error handling with LM Studio.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

try:
    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings
except ImportError as e:
    OpenAIEmbeddings = None
    Chroma = None
    logging.warning(
        f"langchain_openai or langchain_chroma not available: {e}. "
        "RAG functionality disabled."
    )

# Import our custom LM Studio embeddings
from .lm_studio_embeddings import LMStudioEmbeddings


class RagService:
    """
    A service to handle Retrieval-Augmented Generation (RAG) operations.
    
    This service provides:
    - Efficient embedding generation using OpenAI-compatible embeddings
    - Optimized document chunking and storage
    - Smart similarity search with configurable thresholds
    - Robust error handling and fallback mechanisms
    - Performance monitoring and statistics
    """

    def __init__(
        self,
        embedding_model_name: str = "text-embedding-all-minilm-l6-v2-embedding",
        base_url: str = "http://localhost:1234",
        persist_directory: str = ".chromadb",
        chunk_size: int = 500,
        chunk_overlap: int = 100,
        api_key: str = "lm-studio"
    ):
        """
        Initialize the RAG service.
        
        Args:
            embedding_model_name: Name of the embedding model to use
            base_url: Base URL for LM Studio server
            persist_directory: Directory to persist vector store
            chunk_size: Default size of each chunk in characters
            chunk_overlap: Default overlap between chunks in characters
            api_key: API key for LM Studio (default: "lm-studio")
        """
        self.logger = logging.getLogger(__name__)
        self.embedding_model_name = embedding_model_name
        self.base_url = base_url
        self.persist_directory = persist_directory
        self.default_chunk_size = chunk_size
        self.default_chunk_overlap = chunk_overlap
        self.api_key = api_key
        
        self.embeddings: Optional[OpenAIEmbeddings] = None
        self.vectorstore: Optional[Chroma] = None

        # Initialize RAG components
        self._initialize_rag()

    def _initialize_rag(self) -> None:
        """Initialize the embedding model and vector database using LangChain."""
        if OpenAIEmbeddings is None:
            self.logger.warning(
                "OpenAIEmbeddings not available. RAG functionality disabled."
            )
            return

        try:
            # Use our custom LM Studio embeddings that work correctly with the API
            self.embeddings = LMStudioEmbeddings(
                model=self.embedding_model_name, 
                base_url=self.base_url,
                api_key=self.api_key
            )
            self.logger.info(
                f"Initialized LMStudioEmbeddings with model: {self.embedding_model_name} "
                f"at {self.base_url}"
            )

            # Initialize LangChain's Chroma vector store with persistence
            self.vectorstore = Chroma(
                embedding_function=self.embeddings, 
                persist_directory=self.persist_directory
            )
            self.logger.info(
                f"Initialized Chroma vector store at {self.persist_directory}"
            )

        except Exception as e:
            self.logger.error(f"Error initializing RAG: {e}")
            raise

    def check_embedding_model(self, model_name: Optional[str] = None) -> bool:
        """
        Check if the specified embedding model is available in LM Studio.
        
        Args:
            model_name: Name of the model to check (uses instance model if None)

        Returns:
            True if the model is available, False otherwise
        """
        check_model = model_name or self.embedding_model_name
        if self.embeddings is None:
            return False

        try:
            # Try to initialize the embeddings with the model
            temp_embeddings = LMStudioEmbeddings(
                model=check_model, 
                base_url=self.base_url,
                api_key=self.api_key
            )
            # Test with a simple text
            temp_embeddings.embed_documents(["test"])
            return True
        except Exception as e:
            self.logger.warning(f"Model '{check_model}' not available in LM Studio: {e}")
            return False

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text strings using LangChain's OpenAIEmbeddings.
        
        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors

        Raises:
            RuntimeError: If embedding service is not available or fails
        """
        if self.embeddings is None:
            raise RuntimeError("OpenAIEmbeddings not initialized")

        if not texts:
            return []

        try:
            # Use our custom LM Studio embeddings
            embeddings = self.embeddings.embed_documents(texts)
            self.logger.info(f"Generated embeddings for {len(texts)} texts")
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
            chunk_size: Size of each chunk in characters (uses default if None)
            chunk_overlap: Overlap between chunks in characters (uses default if None)

        Returns:
            True if context was stored successfully

        Raises:
            RuntimeError: If vector database is initialized but operation fails
        """
        if self.vectorstore is None:
            self.logger.warning(
                "Vector database not available - skipping context storage"
            )
            return False

        try:
            # Use provided chunking parameters or defaults
            actual_chunk_size = chunk_size or self.default_chunk_size
            actual_chunk_overlap = chunk_overlap or self.default_chunk_overlap
            
            # Generate chunks with optimized size
            chunks = self._chunk_text(text_content, actual_chunk_size, actual_chunk_overlap)
            
            if not chunks:
                self.logger.warning(f"No chunks generated for document {document_id}")
                return False

            # Generate embeddings for chunks
            self.generate_embeddings(chunks)

            # Store each chunk with its embedding and metadata
            ids = [f"{document_id}_{i}" for i in range(len(chunks))]

            self.vectorstore.add_texts(
                texts=chunks,
                metadatas=[
                    {
                        "chunk_index": i, 
                        "chunk_size": len(chunk),
                        **(metadata or {})
                    } 
                    for i, chunk in enumerate(chunks)
                ],
                ids=ids,
            )

            self.logger.info(
                f"Stored {len(chunks)} chunks for document {document_id} "
                f"(chunk size: {actual_chunk_size}, overlap: {actual_chunk_overlap})"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error storing context for document {document_id}: {e}")
            raise

    def retrieve_context(
        self, 
        query: str, 
        n_results: int = 5, 
        min_relevance_score: float = 0.3,
        filter_metadata: Optional[Dict[str, Any]] = None
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

        Raises:
            RuntimeError: If vector database is initialized but operation fails
        """
        if self.vectorstore is None:
            self.logger.warning(
                "Vector database not available - returning empty results"
            )
            return [], []

        try:
            # Build filter if provided
            search_filter = filter_metadata if filter_metadata else None
            
            # Query the vector store with optional filtering
            results = self.vectorstore.similarity_search_with_score(
                query, 
                k=n_results,
                filter=search_filter
            )

            documents = [doc.page_content for doc in results]
            metadatas = [doc.metadata for doc in results]
            scores = [score for _, score in results]

            # Filter by minimum relevance score and convert to similarity
            filtered_docs = []
            filtered_meta = []

            for doc, meta, score in zip(documents, metadatas, scores):
                # Convert distance to similarity score (0 to 1 scale)
                # Distance of 0 = perfect match, higher values = less similar
                similarity_score = max(0, 1 - (score / 2)) if score <= 2 else 0

                if similarity_score >= min_relevance_score:
                    filtered_docs.append(doc)
                    # Add similarity score to metadata
                    meta_copy = meta.copy()
                    meta_copy["similarity_score"] = round(similarity_score, 3)
                    meta_copy["distance"] = round(score, 3)
                    filtered_meta.append(meta_copy)

            self.logger.info(
                f"Retrieved {len(filtered_docs)} relevant chunks for query: "
                f"{query[:50]}... (threshold: {min_relevance_score})"
            )
            return filtered_docs, filtered_meta

        except Exception as e:
            self.logger.error(f"Error retrieving context: {e}")
            raise

    def _chunk_text(
        self, 
        text: str, 
        chunk_size: int = 1000, 
        chunk_overlap: int = 200
    ) -> List[str]:
        """
        Split text into overlapping chunks for better retrieval.
        
        Args:
            text: Input text to chunk
            chunk_size: Size of each chunk in characters
            chunk_overlap: Overlap between chunks in characters

        Returns:
            List of text chunks
        """
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
        """
        Clear all stored context from the vector database.
        
        Returns:
            True if context was cleared successfully
        """
        try:
            if self.vectorstore is not None:
                # Delete all documents from vector store
                self.vectorstore.delete(where={})
                self.logger.info("Cleared all document context")
            return True
        except Exception as e:
            self.logger.error(f"Error clearing context: {e}")
            raise

    def get_context_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the stored context.
        
        Returns:
            Dictionary containing statistics including count and size
        """
        stats = {
            "count": 0, 
            "size_mb": 0.0,
            "embedding_model": self.embedding_model_name,
            "persist_directory": self.persist_directory
        }

        try:
            if self.vectorstore is not None:
                # Get collection metadata
                collection = self.vectorstore.get()
                stats["count"] = len(collection["ids"])
                stats["size_mb"] = round(len(str(collection)) / (1024 * 1024), 2)
                
                # Add chunking configuration
                stats["default_chunk_size"] = self.default_chunk_size
                stats["default_chunk_overlap"] = self.default_chunk_overlap

        except Exception as e:
            self.logger.warning(f"Error getting context stats: {e}")

        return stats

    def update_chunking_config(self, chunk_size: int, chunk_overlap: int) -> None:
        """
        Update the default chunking configuration.
        
        Args:
            chunk_size: New default chunk size
            chunk_overlap: New default chunk overlap
        """
        self.default_chunk_size = chunk_size
        self.default_chunk_overlap = chunk_overlap
        self.logger.info(
            f"Updated chunking config: size={chunk_size}, overlap={chunk_overlap}"
        )
