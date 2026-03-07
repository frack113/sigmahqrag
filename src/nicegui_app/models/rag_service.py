"""
RAG Service for NiceGUI with LangChain integration

Handles Retrieval-Augmented Generation (RAG) operations using LangChain's embedding models and vector stores.
"""

import logging
from typing import Optional, Dict, Any, List, Tuple

try:
    from langchain_ollama import OllamaEmbeddings
    from langchain_chroma import Chroma
except ImportError:
    OllamaEmbeddings = None
    Chroma = None
    logging.warning("langchain_ollama or langchain_chroma not available. RAG functionality disabled.")


class RagService:
    """
    A service to handle Retrieval-Augmented Generation (RAG) operations.

    Methods:
        - generate_embeddings: Create embeddings for text using LangChain's OllamaEmbeddings
        - store_context: Store document context in vector database
        - retrieve_context: Retrieve relevant context using similarity search
        - clear_context: Clear all stored context
        - get_context_stats: Get statistics about stored context
    """

    def __init__(self, embedding_model_name: str = "all-MiniLM-L6-v2"):
        self.logger = logging.getLogger(__name__)
        self.embedding_model_name = embedding_model_name
        self.embeddings = None
        self.vectorstore = None

        # Initialize RAG components
        self._initialize_rag()

    def _initialize_rag(self) -> None:
        """Initialize the embedding model and vector database using LangChain."""
        if OllamaEmbeddings is None:
            self.logger.warning(
                "OllamaEmbeddings not available. RAG functionality disabled."
            )
            return

        try:
            # Initialize LangChain's OllamaEmbeddings
            self.embeddings = OllamaEmbeddings(
                model=self.embedding_model_name, base_url="http://127.0.0.1:1234"
            )
            self.logger.info(
                f"Initialized OllamaEmbeddings with model: {self.embedding_model_name}"
            )

            # Initialize LangChain's Chroma vector store
            self.vectorstore = Chroma(
                embedding_function=self.embeddings, persist_directory=".chromadb"
            )
            self.logger.info("Initialized Chroma vector store for document context")

        except Exception as e:
            self.logger.error(f"Error initializing RAG: {e}")
            raise

    def check_ollama_model(self, model_name: str) -> bool:
        """
        Check if the specified model is available in Ollama.

        Args:
            model_name: Name of the model to check

        Returns:
            True if the model is available, False otherwise
        """
        if self.embeddings is None:
            return False

        try:
            # Try to initialize the embeddings with the model
            OllamaEmbeddings(model=model_name, base_url="http://127.0.0.1:1234")
            # If it doesn't raise an error, the model is available
            return True
        except Exception:
            self.logger.warning(f"Model '{model_name}' not available in Ollama")
            return False

    def pull_ollama_model(self, model_name: str) -> bool:
        """
        Pull a model from Ollama if it's not available locally.

        Args:
            model_name: Name of the model to pull

        Returns:
            True if the model was pulled or already exists, False otherwise
        """
        if self.embeddings is None:
            return False

        try:
            # Try to initialize the embeddings with the model
            OllamaEmbeddings(model=model_name, base_url="http://127.0.0.1:1234")
            self.logger.info(f"Successfully verified model '{model_name}'")
            return True
        except Exception as e:
            self.logger.error(f"Error verifying Ollama model '{model_name}': {e}")
            return False

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of text strings using LangChain's OllamaEmbeddings.

        Args:
            texts (List[str]): List of text strings to embed

        Returns:
            List[List[float]]: List of embedding vectors

        Raises:
            RuntimeError: If embedding service is not available or fails
        """
        if self.embeddings is None:
            raise RuntimeError("OllamaEmbeddings not initialized")

        if not texts:
            return []

        try:
            # Use LangChain's OllamaEmbeddings to generate embeddings
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
        chunk_size: int = 500,
        overlap: int = 100,
    ) -> bool:
        """
        Store document context in the vector database.

        Args:
            document_id (str): Unique identifier for the document
            text_content (str): Text content to store and index
            metadata (Optional[Dict[str, Any]]): Additional metadata about the document
            chunk_size (int): Size of each chunk in characters
            overlap (int): Overlap between chunks in characters

        Returns:
            bool: True if context was stored successfully

        Raises:
            RuntimeError: If vector database is initialized but operation fails
        """
        if self.vectorstore is None:
            self.logger.warning(
                "Vector database not available - skipping context storage"
            )
            return False

        try:
            # Generate embedding for the text content
            chunks = self._chunk_text(text_content, chunk_size, overlap)
            self.generate_embeddings(chunks)

            # Store each chunk with its embedding
            ids = [f"{document_id}_{i}" for i in range(len(chunks))]

            self.vectorstore.add_texts(
                texts=chunks,
                metadatas=[
                    {"chunk_index": i, **(metadata or {})} for i in range(len(chunks))
                ],
                ids=ids,
            )

            self.logger.info(f"Stored {len(chunks)} chunks for document {document_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error storing context: {e}")
            raise

    def retrieve_context(
        self, query: str, n_results: int = 5, min_relevance_score: float = 0.3
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
        if self.vectorstore is None:
            self.logger.warning(
                "Vector database not available - returning empty results"
            )
            return [], []

        try:
            # Query the vector store
            results = self.vectorstore.similarity_search_with_score(query, k=n_results)

            documents = [doc.page_content for doc in results]
            metadatas = [doc.metadata for doc in results]
            scores = [score for _, score in results]

            # Filter by minimum relevance score
            filtered_docs = []
            filtered_meta = []

            for doc, meta, score in zip(documents, metadatas, scores):
                # Convert distance to similarity score
                # Distance of 0 = perfect match, 2 = opposite
                # We'll use a simple transformation: similarity = 1 - (distance / 2)
                similarity_score = 1 - (score / 2) if score <= 2 else 0

                if similarity_score >= min_relevance_score:
                    filtered_docs.append(doc)
                    # Add similarity score to metadata
                    meta_copy = meta.copy()
                    meta_copy["similarity_score"] = round(similarity_score, 3)
                    filtered_meta.append(meta_copy)

            self.logger.info(
                f"Retrieved {len(filtered_docs)} relevant chunks for query: {query[:50]}..."
            )
            return filtered_docs, filtered_meta

        except Exception as e:
            self.logger.error(f"Error retrieving context: {e}")
            raise

    def _chunk_text(
        self, text: str, chunk_size: int = 500, overlap: int = 100
    ) -> List[str]:
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
            Dict[str, Any]: Statistics including count and size
        """
        stats = {"count": 0, "size_mb": 0.0}

        try:
            if self.vectorstore is not None:
                # Get collection metadata
                collection = self.vectorstore.get()
                stats["count"] = len(collection["ids"])
                stats["size_mb"] = round(len(str(collection)) / (1024 * 1024), 2)

        except Exception as e:
            self.logger.warning(f"Error getting context stats: {e}")

        return stats
