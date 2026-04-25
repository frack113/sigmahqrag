"""Tests for embeddings module."""

import pytest
from llama_index.core.schema import Document


class TestEmbeddingGenerator:
    """Test EmbeddingGenerator class."""

    def test_init_defaults(self):
        """Test default initialization."""
        from src.rag.embeddings import EmbeddingGenerator

        generator = EmbeddingGenerator()
        assert generator.batch_size == 32
        assert generator.embedding_dim == 384

    def test_init_custom(self):
        """Test custom initialization."""
        from src.rag.embeddings import EmbeddingGenerator

        generator = EmbeddingGenerator(batch_size=64, embedding_dim=512)
        assert generator.batch_size == 64
        assert generator.embedding_dim == 512


class TestEmbedDocuments:
    """Test embed_documents function."""

    @pytest.mark.asyncio
    async def test_empty_documents(self):
        """Test with empty documents."""
        from src.rag.embeddings import embed_documents

        result = await embed_documents([])
        assert result == []

    @pytest.mark.asyncio
    async def test_single_document(self):
        """Test with single document."""
        from src.rag.embeddings import embed_documents

        docs = [Document(text="Test document", metadata={})]
        result = await embed_documents(docs)
        assert isinstance(result, list)


class TestGetEmbeddingModel:
    """Test get_embedding_model function."""

    def test_model_returns_object(self):
        """Test that model returns an object."""
        from src.rag.embeddings import get_embedding_model

        model = get_embedding_model()
        assert model is not None

    @pytest.mark.skip(reason="Requires HF token for model download")
    def test_model_has_embed_method(self):
        """Test that model has embed method."""
        from src.rag.embeddings import get_embedding_model

        model = get_embedding_model()
        assert hasattr(model, "embed_documents")
        assert hasattr(model, "aembed_documents")


class TestAirGappedConfig:
    """Test air-gapped configuration."""

    def test_env_var_local_no_model_raises(self, monkeypatch):
        """Test SIGMA_RAG_EMBED_MODEL=local raises when no GGUF."""
        monkeypatch.setenv("SIGMA_RAG_EMBED_MODEL", "local")

        import src.rag.embeddings as emb_module
        emb_module._embed_model = None

        with pytest.raises(EnvironmentError, match="no GGUF model"):
            emb_module.get_embedding_model()

    def test_singleton_pattern(self):
        """Test that model is reused (singleton)."""
        from src.rag.embeddings import get_embedding_model

        model1 = get_embedding_model()
        model2 = get_embedding_model()
        assert model1 is model2
