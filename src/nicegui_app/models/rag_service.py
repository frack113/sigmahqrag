"""
RAG Service for NiceGUI - Simple interface for RAG operations

This module provides a simple interface to the optimized RAG service,
making it easier to use in the DataService and other components.
"""

from .rag_service_optimized import OptimizedRAGService, create_rag_service
from typing import List, Dict, Any, Optional, Tuple


class RagService:
    """
    Simple RAG service interface that wraps the optimized RAG service.
    
    This provides a simplified API for basic RAG operations while
    leveraging the full power of the optimized implementation.
    """

    def __init__(self, embedding_model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the RAG service.
        
        Args:
            embedding_model_name: Name of the embedding model to use
        """
        # Create optimized RAG service with default configuration
        self._rag_service = create_rag_service(
            embedding_model_name=embedding_model_name,
            persist_directory=".chromadb",
            chunk_size=500,
            chunk_overlap=100,
            collection_name="rag_collection"
        )

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text strings.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        import asyncio
        
        try:
            # Run async method in a new event loop
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                embeddings = loop.run_until_complete(
                    self._rag_service.generate_embeddings(texts)
                )
                return embeddings
            finally:
                loop.close()
        except Exception as e:
            # Fallback to empty embeddings if async fails
            return [[] for _ in texts]

    def store_context(
        self,
        document_id: str,
        text_content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Store document context in the vector database.
        
        Args:
            document_id: Unique identifier for the document
            text_content: Text content to store and index
            metadata: Additional metadata about the document
            
        Returns:
            True if context was stored successfully
        """
        return self._rag_service.store_context(
            document_id=document_id,
            text_content=text_content,
            metadata=metadata
        )

    def retrieve_context(
        self,
        query: str,
        n_results: int = 5,
        min_relevance_score: float = 0.3,
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Retrieve relevant context using similarity search.
        
        Args:
            query: The search query
            n_results: Maximum number of results to return
            min_relevance_score: Minimum relevance score threshold (0.0 to 1.0)
            
        Returns:
            Tuple of (relevant document chunks, metadata for each chunk)
        """
        return self._rag_service.retrieve_context(
            query=query,
            n_results=n_results,
            min_relevance_score=min_relevance_score
        )

    def clear_context(self) -> bool:
        """Clear all stored context from the vector database."""
        return self._rag_service.clear_context()

    def get_context_stats(self) -> Dict[str, Any]:
        """Get statistics about the stored context."""
        return self._rag_service.get_context_stats()

    def check_ollama_model(self, model_name: str) -> bool:
        """
        Check if an Ollama model is available.
        
        Args:
            model_name: Name of the model to check
            
        Returns:
            True if the model is available
        """
        # For now, return True as we're using LM Studio
        # This method is kept for compatibility
        return True

    def pull_ollama_model(self, model_name: str) -> bool:
        """
        Pull an Ollama model (not used with LM Studio).
        
        Args:
            model_name: Name of the model to pull
            
        Returns:
            True (always returns True for LM Studio compatibility)
        """
        # For LM Studio, models are already available
        # This method is kept for compatibility
        return True

    def check_availability(self) -> bool:
        """Check if the RAG service is available."""
        return self._rag_service.check_availability()

    def cleanup(self):
        """Clean up resources."""
        self._rag_service.cleanup()