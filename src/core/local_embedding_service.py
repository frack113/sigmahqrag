"""
Local Embedding Service for SigmaHQ RAG application.

Provides standalone CPU-based embeddings using sentence-transformers with direct
safetensors model file loading. No external API dependencies required.

Uses Gradio's native queuing system - simple synchronous methods.
"""

import logging
import time
from pathlib import Path
from typing import Any


class LocalEmbeddingService:
    """
    Local embedding service using sentence-transformers.

    Features:
    - CPU-based embeddings with direct safetensors loading
    - No external API dependencies (LM Studio not required)
    - Simple synchronous methods (Gradio queue=True handles async)
    """

    # Default model path - use the local safetensors file
    DEFAULT_MODEL_PATH = (
        Path(__file__).parent.parent.parent
        / "data"
        / "models"
        / "all-MiniLM-L6-v2.safetensors"
    )

    def __init__(self):
        """Initialize the local embedding service."""
        self.logger = logging.getLogger(__name__)
        self.model = None
        self._model_loaded = False
        self._start_time = time.time()
        self.collection = None

        # Statistics
        self.total_embeddings = 0
        self.failed_embeddings = 0
        self.average_response_time = 0.0
        self.last_error = None

    def initialize(self) -> bool:
        """Initialize the embedding service."""
        if self._model_loaded:
            return True

        try:
            from sentence_transformers import SentenceTransformer

            model_path = str(self.DEFAULT_MODEL_PATH)

            # Check if safetensors file exists
            if not Path(model_path).exists():
                self.logger.error(f"Model file not found: {model_path}")
                return False

            self.model = SentenceTransformer(
                model_path,
                device="cpu",  # Force CPU for local embeddings
            )

            # Test the model with a simple embedding
            test_embedding = self.model.encode(["test"])
            if len(test_embedding) == 384:  # MiniLM produces 384-dim embeddings
                self._model_loaded = True
                self.logger.info(
                    f"Model loaded successfully. Embedding dimension: {len(test_embedding)}"
                )
                return True
            else:
                self.logger.error(
                    f"Unexpected embedding dimension: {len(test_embedding)}"
                )
                return False

        except ImportError as e:
            self.logger.error(f"sentence-transformers not available: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error loading model: {e}")
            self.last_error = str(e)
            return False

    def cleanup(self):
        """Clean up resources."""
        try:
            if self.model is not None:
                del self.model
                self.model = None
            self._model_loaded = False
            if self.collection is not None:
                self.collection = None
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")

    def generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings using local sentence-transformers model.

        Gradio's queue=True handles async execution automatically.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        # Ensure model is loaded
        if self.model is None or not self._model_loaded:
            if not self.initialize():
                raise Exception("Failed to initialize local embedding model")

        # Generate embeddings synchronously (Gradio handles async via queue=True)
        embeddings = self.model.encode(texts, convert_to_numpy=True)

        return embeddings.tolist()

    def get_embedding_stats(self) -> dict[str, Any]:
        """Get embedding service statistics."""
        return {
            "total_embeddings": self.total_embeddings,
            "failed_embeddings": self.failed_embeddings,
            "average_response_time": self.average_response_time,
            "last_error": self.last_error,
            "uptime_seconds": time.time() - self._start_time,
            "model_loaded": self._model_loaded,
        }

    def get_health_status(self) -> dict[str, Any]:
        """Get service health status."""
        issues = []

        # Check if model is loaded
        if self.model is None and not self._model_loaded:
            issues.append("Embedding model not loaded")

        return {
            "service": "local_embedding_service",
            "status": "healthy" if len(issues) == 0 else "unhealthy",
            "issues": issues,
            "timestamp": time.time(),
            "stats": self.get_embedding_stats(),
        }

    def query(
        self,
        query_texts: list[str],
        n_results: int = 3,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Query the ChromaDB collection for relevant documents.

        Args:
            query_texts: List of text to search for
            n_results: Number of results to return
            min_score: Minimum similarity score threshold

        Returns:
            List of matching documents with metadata
        """
        if not self.collection or not self._model_loaded:
            return []

        try:
            from sentence_transformers import SentenceTransformer

            if not isinstance(self.model, SentenceTransformer):
                # Initialize model if not already loaded
                if not self.initialize():
                    return []

            # Generate query embeddings
            query_embeddings = self.model.encode(
                query_texts, convert_to_numpy=True, normalize_embeddings=True
            ).tolist()

            # Query ChromaDB
            results = self.collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )

            # Filter by minimum score and format results
            filtered_results = []
            for i, doc_list in enumerate(results["ids"]):
                for j, doc_id in enumerate(doc_list):
                    distance = results["distances"][i][j] if results["distances"] else 0
                    if distance < min_score:
                        continue

                    metadata = results["metadatas"][i][j] or {}
                    filtered_results.append(
                        {
                            "id": doc_id,
                            "content": metadata.get("text", ""),
                            "score": 1 - distance,
                            "metadata": metadata,
                        }
                    )

            return filtered_results

        except Exception as e:
            self.logger.error(f"Query error: {e}")
            return []

    def add(
        self, texts: list[str], metadatas: list[dict[str, Any]] | None = None
    ) -> bool:
        """
        Add documents to the ChromaDB collection.

        Args:
            texts: List of text documents to add
            metadatas: Optional metadata for each document

        Returns:
            True if successful, False otherwise
        """
        if not self.collection or not self._model_loaded:
            return False

        try:
            from sentence_transformers import SentenceTransformer

            if not isinstance(self.model, SentenceTransformer):
                if not self.initialize():
                    return False

            # Generate embeddings
            embeddings = self.model.encode(
                texts, convert_to_numpy=True, normalize_embeddings=True
            ).tolist()

            # Add to collection
            if metadatas is None:
                metadatas = [{"index": i} for i in range(len(texts))]

            ids = [f"doc_{i}" for i in range(len(texts))]
            self.collection.add(
                embeddings=embeddings,
                ids=ids,
                documents=texts,
                metadatas=metadatas,
            )

            self.total_embeddings += len(texts)
            return True

        except Exception as e:
            self.logger.error(f"Add error: {e}")
            return False

    def get_collection_count(self) -> int:
        """Get the number of documents in the collection."""
        if not self.collection:
            return 0
        try:
            count_data = self.collection.get()
            return len(count_data["ids"][0]) if count_data["ids"] else 0
        except Exception:
            return 0

    def get_usage_stats(self) -> dict[str, Any]:
        """Get comprehensive usage statistics."""
        return {
            "model_path": str(self.DEFAULT_MODEL_PATH),
            "stats": self.get_embedding_stats(),
            "health": self.get_health_status(),
            "collection_count": self.get_collection_count(),
        }


# Factory function for convenience
def create_local_embedding_service() -> LocalEmbeddingService:
    """Create a local embedding service instance."""
    return LocalEmbeddingService()
