"""Tests for embedding generation for RAG pipeline."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.back.rag.embeddings import (
    EmbeddingGenerator,
    _check_hf_available,
    embed_documents,
    get_embedding_model,
    store_embeddings,
)


class TestCheckHfAvailable:
    def test_returns_true_when_reachable(self) -> None:
        mock_response = MagicMock(status_code=200)
        with patch("httpx.get", return_value=mock_response):
            assert _check_hf_available() is True

    def test_returns_false_on_exception(self) -> None:
        with patch("httpx.get", side_effect=ValueError("fail")):
            assert _check_hf_available() is False


class TestGetEmbeddingModel:
    def test_returns_cached(self) -> None:
        fake = MagicMock()
        with patch("src.back.rag.embeddings._embed_model", fake):
            result = get_embedding_model()
        assert result is fake

    def test_huggingface_env(self) -> None:
        with (
            patch("src.back.rag.embeddings._embed_model", None),
            patch("llama_index.embeddings.huggingface.HuggingFaceEmbedding") as mock_cls,
            patch.dict("os.environ", {"SIGMA_RAG_EMBED_MODEL": "huggingface"}),
        ):
            result = get_embedding_model()
        mock_cls.assert_called_once_with(
            model_name="intfloat/multilingual-e5-small",
            embed_batch_size=32,
        )
        assert result is not None

    def test_local_gguf(self) -> None:
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.glob.return_value = [MagicMock(__str__=MagicMock(return_value="/fake/model.gguf"))]
        with (
            patch("src.back.rag.embeddings._embed_model", None),
            patch("llama_index.embeddings.huggingface.HuggingFaceEmbedding") as mock_cls,
            patch("src.back.rag.embeddings.EMBEDDINGS_DIR", mock_dir),
        ):
            result = get_embedding_model()
        mock_cls.assert_called_once_with(
            model_name="/fake/model.gguf",
            embed_batch_size=32,
        )
        assert result is not None

    def test_local_env_no_gguf_raises(self) -> None:
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.glob.return_value = []
        with (
            patch("src.back.rag.embeddings._embed_model", None),
            patch("llama_index.embeddings.huggingface.HuggingFaceEmbedding"),
            patch("src.back.rag.embeddings.EMBEDDINGS_DIR", mock_dir),
            patch.dict("os.environ", {"SIGMA_RAG_EMBED_MODEL": "local"}),
            pytest.raises(OSError, match="no GGUF model found"),
        ):
            get_embedding_model()

    def test_hf_fallback(self) -> None:
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.glob.return_value = []
        with (
            patch("src.back.rag.embeddings._embed_model", None),
            patch("llama_index.embeddings.huggingface.HuggingFaceEmbedding") as mock_cls,
            patch("src.back.rag.embeddings.EMBEDDINGS_DIR", mock_dir),
            patch("src.back.rag.embeddings._check_hf_available", return_value=True),
        ):
            result = get_embedding_model()
        mock_cls.assert_called_once_with(
            model_name="intfloat/multilingual-e5-small",
            embed_batch_size=32,
        )
        assert result is not None

    def test_air_gapped_raises(self) -> None:
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        mock_dir.glob.return_value = []
        with (
            patch("src.back.rag.embeddings._embed_model", None),
            patch("llama_index.embeddings.huggingface.HuggingFaceEmbedding"),
            patch("src.back.rag.embeddings.EMBEDDINGS_DIR", mock_dir),
            patch("src.back.rag.embeddings._check_hf_available", return_value=False),
            pytest.raises(OSError, match="Air-gapped environment"),
        ):
            get_embedding_model()

    def test_embeddings_dir_not_exists_hf_fallback(self) -> None:
        mock_dir = MagicMock()
        mock_dir.exists.return_value = False
        with (
            patch("src.back.rag.embeddings._embed_model", None),
            patch("llama_index.embeddings.huggingface.HuggingFaceEmbedding") as mock_cls,
            patch("src.back.rag.embeddings.EMBEDDINGS_DIR", mock_dir),
            patch("src.back.rag.embeddings._check_hf_available", return_value=True),
        ):
            result = get_embedding_model()
        mock_cls.assert_called_once()
        assert result is not None

    def test_gguf_str_method(self) -> None:
        mock_dir = MagicMock()
        mock_dir.exists.return_value = True
        gguf_mock = MagicMock()
        gguf_mock.__str__.return_value = "/fake/path/model.gguf"
        mock_dir.glob.return_value = [gguf_mock]
        with (
            patch("src.back.rag.embeddings._embed_model", None),
            patch("llama_index.embeddings.huggingface.HuggingFaceEmbedding") as mock_cls,
            patch("src.back.rag.embeddings.EMBEDDINGS_DIR", mock_dir),
            patch("src.back.rag.embeddings._check_hf_available"),
        ):
            get_embedding_model()
        mock_cls.assert_called_once_with(
            model_name="/fake/path/model.gguf",
            embed_batch_size=32,
        )


class TestEmbedDocuments:
    @pytest.mark.asyncio
    async def test_returns_empty_for_empty_list(self) -> None:
        result = await embed_documents([])
        assert result == []

    @pytest.mark.asyncio
    async def test_success(self) -> None:
        mock_model = AsyncMock()
        mock_model.aembed_documents = AsyncMock(return_value=[[0.1], [0.2]])
        docs = [MagicMock(text="a"), MagicMock(text="b")]
        with patch("src.back.rag.embeddings.get_embedding_model", return_value=mock_model):
            result = await embed_documents(docs)
        assert result == [[0.1], [0.2]]

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self) -> None:
        with patch("src.back.rag.embeddings.get_embedding_model", side_effect=ValueError("fail")):
            result = await embed_documents([MagicMock(text="a")])
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

    def test_get_embed_model_first_call(self) -> None:
        gen = EmbeddingGenerator()
        assert gen._embed_model is None
        with patch("src.back.rag.embeddings.get_embedding_model", return_value="fake"):
            model = gen._get_embed_model()
        assert model == "fake"
        assert gen._embed_model == "fake"

    def test_get_embed_model_cached(self) -> None:
        gen = EmbeddingGenerator()
        gen._embed_model = "cached"
        with patch("src.back.rag.embeddings.get_embedding_model") as mock_get:
            model = gen._get_embed_model()
        assert model == "cached"
        mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_delegates(self) -> None:
        gen = EmbeddingGenerator()
        docs = [MagicMock(text="x")]
        with patch("src.back.rag.embeddings.embed_documents", AsyncMock(return_value=[[0.1]])):
            result = await gen.generate(docs)
        assert result == [[0.1]]

    @pytest.mark.asyncio
    async def test_store_delegates(self) -> None:
        gen = EmbeddingGenerator()
        docs = [MagicMock(text="x", metadata={})]
        with patch("src.back.rag.embeddings.store_embeddings", AsyncMock(return_value=True)):
            result = await gen.store(docs, [[0.1]])
        assert result is True
