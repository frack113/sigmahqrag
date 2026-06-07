"""Abstract base class for embedding providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from llama_index.core.schema import Document


class EmbeddingProvider(ABC):
    """Abstract interface for embedding providers."""

    @abstractmethod
    async def embed(self, documents: list[Document]) -> list[list[float]]:
        """Generate embeddings for a list of documents.

        Args:
            documents: List of LlamaIndex Documents to embed.

        Returns:
            List of embedding vectors.
        """

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding vector dimension."""


class HuggingFaceEmbeddingProvider(EmbeddingProvider):
    """HuggingFace embedding provider using SentenceTransformer models."""

    def __init__(self, model_name: str, device: str = "cpu") -> None:
        """Initialize HuggingFace embedding provider.

        Args:
            model_name: Model name or path for SentenceTransformer.
            device: Device to run inference on ('cpu', 'cuda', etc.).
        """
        self.model_name = model_name
        self.device = device
        self._model: Any | None = None
        self._dimension: int | None = None

    def _load_model(self) -> Any:
        """Load or return cached SentenceTransformer model."""
        if self._model is None:
            from llama_index.embeddings.huggingface import HuggingFaceEmbedding

            self._model = HuggingFaceEmbedding(
                model_name=self.model_name,
                device=self.device,
            )
            self._dimension = self._detect_dimension()
        return self._model

    def _detect_dimension(self) -> int:
        """Detect embedding dimension from a sample document."""
        sample_text = "Sample text for dimension detection."
        embedding = self._model.get_text_embedding(sample_text)
        return len(embedding)

    async def embed(self, documents: list[Document]) -> list[list[float]]:
        """Generate embeddings using HuggingFace model.

        Args:
            documents: List of LlamaIndex Documents to embed.

        Returns:
            List of embedding vectors.
        """
        if not documents:
            return []

        model = self._load_model()
        texts = [doc.text for doc in documents if doc.text]
        if not texts:
            return []

        embeddings = model._get_text_embeddings(texts)  # noqa: SLF001
        return [list(emb) for emb in embeddings]

    @property
    def dimension(self) -> int:
        """Return the embedding vector dimension."""
        if self._dimension is None:
            self._load_model()
        return self._dimension  # type: ignore[return-value]


__all__ = ["EmbeddingProvider", "HuggingFaceEmbeddingProvider"]
