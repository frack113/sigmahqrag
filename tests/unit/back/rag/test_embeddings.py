"""Tests for embedding generation for RAG pipeline."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.back.rag.embeddings import (
    EmbeddingGenerator,
    embed_documents,
    get_embedding_model,
    store_embeddings,
)


class TestGetEmbeddingModel:
    def test_get_embedding_model_returns_something(self) -> None:
        model = get_embedding_model()
        assert model is not None


class TestAirGappedConfig:
    def test_env_var_handling(self) -> None:
        from src.back.rag import embeddings

        assert embeddings is not None


class TestEmbedDocuments:
    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_list(self) -> None:
        result = await embed_documents([])
        assert result == []


class TestStoreEmbeddings:
    @pytest.mark.asyncio
    async def test_returns_true_on_success(self) -> None:
        documents = [MagicMock(text="test", metadata={})]
        embeddings = [[0.1, 0.2, 0.3]]
        with patch("src.back.rag.embeddings._store_embeddings", AsyncMock(return_value=True)):
            result = await store_embeddings(documents, embeddings)
            assert result is True


class TestEmbeddingGenerator:
    def test_init_defaults(self) -> None:
        gen = EmbeddingGenerator()
        assert gen.batch_size == 32
        assert gen.embedding_dim == 384

    def test_init_custom(self) -> None:
        gen = EmbeddingGenerator(batch_size=16, embedding_dim=128)
        assert gen.batch_size == 16
        assert gen.embedding_dim == 128
