"""
Local Embedding Service for SigmaHQ RAG application.

Provides standalone CPU-based embeddings using sentence-transformers with direct
safetensors model file loading. No external API dependencies required.

Uses Gradio's native queuing system - simple synchronous methods.
"""

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
        self.model = None
        self._model_loaded = False
        self._start_time = time.time()

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
                print(f"Model file not found: {model_path}")
                return False

            self.model = SentenceTransformer(
                model_path,
                device="cpu",  # Force CPU for local embeddings
            )

            # Test the model with a simple embedding
            test_embedding = self.model.encode(["test"])
            if len(test_embedding) == 384:  # MiniLM produces 384-dim embeddings
                self._model_loaded = True
                print(
                    f"Model loaded successfully. Embedding dimension: {len(test_embedding)}"
                )
                return True
            else:
                print(f"Unexpected embedding dimension: {len(test_embedding)}")
                return False

        except ImportError as e:
            print(f"sentence-transformers not available: {e}")
            return False
        except Exception as e:
            print(f"Error loading model: {e}")
            self.last_error = str(e)
            return False

    def cleanup(self):
        """Clean up resources."""
        try:
            if self.model is not None:
                del self.model
                self.model = None
            self._model_loaded = False

        except Exception as e:
            print(f"Error during cleanup: {e}")

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

    def get_usage_stats(self) -> dict[str, Any]:
        """Get comprehensive usage statistics."""
        return {
            "model_path": str(self.DEFAULT_MODEL_PATH),
            "stats": self.get_embedding_stats(),
            "health": self.get_health_status(),
        }


# Factory function for convenience
def create_local_embedding_service() -> LocalEmbeddingService:
    """Create a local embedding service instance."""
    return LocalEmbeddingService()
