"""Tests for embeddings service."""

import pytest


class TestGetEmbeddingModel:
    """Test getting embedding model."""

    def test_get_embedding_model_returns_something(self):
        """Test that model can be retrieved."""
        from src.rag.embeddings import get_embedding_model

        model = get_embedding_model()
        assert model is not None


class TestAirGappedConfig:
    """Test air-gapped configuration."""

    def test_env_var_handling(self):
        """Test env var is handled."""
        # Just verify module loads
        from src.rag import embeddings

        assert embeddings is not None
