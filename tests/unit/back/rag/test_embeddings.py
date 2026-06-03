"""Tests for embedding generation for RAG pipeline."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.rag.embeddings import (
    EmbeddingGenerator,
    embed_documents,
    get_embedding_model,
    store_embeddings,
)


class TestGetEmbeddingModel:
    def test_returns_cached(self) -> None:
        fake = MagicMock()
        with patch("src.rag.embeddings._embed_model", fake):
            result = get_embedding_model()
        assert result is fake

    def test_uses_config_from_db(self) -> None:
        mock_db = MagicMock()
        mock_db.get_embedding_config.return_value = {"model": "custom/model"}
        with (
            patch("src.rag.embeddings._embed_model", None),
            patch("src.rag.embeddings.DatabaseService.get_instance", return_value=mock_db),
            patch("src.rag.ingestion.build_embed_model") as mock_build,
        ):
            mock_build.return_value = "fake_model"
            result = get_embedding_model()
        mock_build.assert_called_once_with("custom/model")
        assert result == "fake_model"

    def test_falls_back_to_default(self) -> None:
        mock_db = MagicMock()
        mock_db.get_embedding_config.return_value = {}
        with (
            patch("src.rag.embeddings._embed_model", None),
            patch("src.rag.embeddings.DatabaseService.get_instance", return_value=mock_db),
            patch("src.rag.ingestion.build_embed_model") as mock_build,
        ):
            mock_build.return_value = "default_model"
            result = get_embedding_model()
        from src.rag.ingestion import DEFAULT_MODEL

        mock_build.assert_called_once_with(DEFAULT_MODEL)
        assert result == "default_model"


class TestEmbedDocuments:
    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_list(self) -> None:
        result = await embed_documents([])
        assert result == []

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        mock_model = MagicMock()
        mock_model.get_text_embedding_batch = MagicMock(return_value=[[0.1], [0.2]])
        docs = [MagicMock(text="a"), MagicMock(text="b")]
        with patch("src.rag.embeddings.get_embedding_model", return_value=mock_model):
            result = await embed_documents(docs)
        assert result == [[0.1], [0.2]]

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self) -> None:
        with patch("src.rag.embeddings.get_embedding_model", side_effect=ValueError("fail")):
            result = await embed_documents([MagicMock(text="a")])
        assert result == []


class TestStoreEmbeddings:
    @pytest.mark.asyncio
    async def test_returns_true_on_success(self) -> None:
        documents = [MagicMock(text="test", metadata={})]
        embeddings = [[0.1, 0.2, 0.3]]
        with patch("src.rag.embeddings._store_embeddings", AsyncMock(return_value=True)):
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

    def test_get_embed_model_first_call(self) -> None:
        gen = EmbeddingGenerator()
        assert gen._embed_model is None
        with patch("src.rag.embeddings.get_embedding_model", return_value="fake"):
            model = gen._get_embed_model()
        assert model == "fake"
        assert gen._embed_model == "fake"

    def test_get_embed_model_cached(self) -> None:
        gen = EmbeddingGenerator()
        gen._embed_model = "cached"
        with patch("src.rag.embeddings.get_embedding_model") as mock_get:
            model = gen._get_embed_model()
        assert model == "cached"
        mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_delegates(self) -> None:
        gen = EmbeddingGenerator()
        docs = [MagicMock(text="x")]
        with patch("src.rag.embeddings.embed_documents", AsyncMock(return_value=[[0.1]])):
            result = await gen.generate(docs)
        assert result == [[0.1]]

    @pytest.mark.asyncio
    async def test_store_delegates(self) -> None:
        gen = EmbeddingGenerator()
        docs = [MagicMock(text="x", metadata={})]
        with patch("src.rag.embeddings.store_embeddings", AsyncMock(return_value=True)):
            result = await gen.store(docs, [[0.1]])
        assert result is True
