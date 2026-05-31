"""Tests for RAG search functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.back.rag.search import (
    SearchEngine,
    _get_search_embed_model,
    format_search_result,
    get_citation,
    search,
)


class TestSearchEngine:
    def test_init_defaults(self) -> None:
        engine = SearchEngine()
        assert engine.collection_names == ["sigma_rules", "sigma_docs", "sigma_spec"]
        assert engine.top_k == 15
        assert engine.similarity_threshold == 0.0

    def test_init_custom(self) -> None:
        engine = SearchEngine(collection_names=["custom"], top_k=5, similarity_threshold=0.5)
        assert engine.collection_names == ["custom"]
        assert engine.top_k == 5
        assert engine.similarity_threshold == 0.5

    def test_format_result_delegates(self) -> None:
        engine = SearchEngine()
        raw = {"text": "test", "score": 0.9, "metadata": {"file_path": "f.yaml", "line_start": 1}}
        result = engine.format_result(raw)
        assert result["text"] == "test"

    def test_get_citation_delegates(self) -> None:
        engine = SearchEngine()
        result = engine.get_citation({"metadata": {"file_path": "f.yaml", "line_start": "5"}})
        assert result == "f.yaml:5"


class TestGetSearchEmbedModel:
    def test_first_call_creates_model(self) -> None:
        mock_db = MagicMock()
        mock_db.get_embedding_config.return_value = {}
        with (
            patch("src.back.rag.search._async_embed_model", None),
            patch("src.back.rag.search.DatabaseService.get_instance", return_value=mock_db),
            patch("src.back.rag.search.build_embed_model") as mock_build,
        ):
            from src.back.rag.ingestion import DEFAULT_MODEL

            _get_search_embed_model()
        mock_build.assert_called_once_with(DEFAULT_MODEL)

    def test_subsequent_call_returns_cached(self) -> None:
        mock_db = MagicMock()
        mock_db.get_embedding_config.return_value = {}
        with (
            patch("src.back.rag.search._async_embed_model", None),
            patch("src.back.rag.search.DatabaseService.get_instance", return_value=mock_db),
            patch("src.back.rag.search.build_embed_model") as mock_build,
        ):
            mock_build.return_value = "fake_model"
            first = _get_search_embed_model()
            second = _get_search_embed_model()
        assert first is second
        mock_build.assert_called_once()


class TestSearch:
    @pytest.mark.asyncio
    async def test_empty_query(self) -> None:
        result = await search("")
        assert result == []

    @pytest.mark.asyncio
    async def test_no_scored_points(self) -> None:
        mock_client = MagicMock()
        mock_client.query_points.return_value = MagicMock(points=[])
        mock_embed = AsyncMock()
        mock_embed.aget_query_embedding = AsyncMock(return_value=[0.1])
        with (
            patch("src.back.rag.search.get_qdrant_client", return_value=mock_client),
            patch("src.back.rag.search._get_search_embed_model", return_value=mock_embed),
        ):
            results = await search("query")
        assert results == []

    @pytest.mark.asyncio
    async def test_flat_payload(self) -> None:
        point = MagicMock()
        point.score = 0.9
        point.payload = {"text": "hello", "source": "x.yaml"}
        mock_client = MagicMock()
        mock_client.query_points.return_value = MagicMock(points=[point])
        mock_embed = AsyncMock()
        mock_embed.aget_query_embedding = AsyncMock(return_value=[0.1])
        with (
            patch("src.back.rag.search.get_qdrant_client", return_value=mock_client),
            patch("src.back.rag.search._get_search_embed_model", return_value=mock_embed),
        ):
            results = await search("query")
        assert len(results) == 1
        assert results[0]["text"] == "hello"
        assert results[0]["score"] == 0.9

    @pytest.mark.asyncio
    async def test_node_content_json_string(self) -> None:
        point = MagicMock()
        point.score = 0.8
        point.payload = {"_node_content": '{"text": "nested", "metadata": {"src": "a.yaml"}}'}
        mock_client = MagicMock()
        mock_client.query_points.return_value = MagicMock(points=[point])
        mock_embed = AsyncMock()
        mock_embed.aget_query_embedding = AsyncMock(return_value=[0.1])
        with (
            patch("src.back.rag.search.get_qdrant_client", return_value=mock_client),
            patch("src.back.rag.search._get_search_embed_model", return_value=mock_embed),
        ):
            results = await search("query")
        assert len(results) == 1
        assert results[0]["text"] == "nested"
        assert results[0]["metadata"] == {"src": "a.yaml"}

    @pytest.mark.asyncio
    async def test_node_content_dict(self) -> None:
        point = MagicMock()
        point.score = 0.7
        point.payload = {"_node_content": {"text": "dict text", "metadata": {"k": "v"}}}
        mock_client = MagicMock()
        mock_client.query_points.return_value = MagicMock(points=[point])
        mock_embed = AsyncMock()
        mock_embed.aget_query_embedding = AsyncMock(return_value=[0.1])
        with (
            patch("src.back.rag.search.get_qdrant_client", return_value=mock_client),
            patch("src.back.rag.search._get_search_embed_model", return_value=mock_embed),
        ):
            results = await search("query")
        assert len(results) == 1
        assert results[0]["text"] == "dict text"
        assert results[0]["metadata"] == {"k": "v"}

    @pytest.mark.asyncio
    async def test_node_content_json_decode_error_falls_back(self) -> None:
        point = MagicMock()
        point.score = 0.6
        point.payload = {"_node_content": "invalid json!!", "extra": "meta"}
        mock_client = MagicMock()
        mock_client.query_points.return_value = MagicMock(points=[point])
        mock_embed = AsyncMock()
        mock_embed.aget_query_embedding = AsyncMock(return_value=[0.1])
        with (
            patch("src.back.rag.search.get_qdrant_client", return_value=mock_client),
            patch("src.back.rag.search._get_search_embed_model", return_value=mock_embed),
        ):
            results = await search("query")
        assert len(results) == 1
        assert results[0]["text"] == ""
        assert results[0]["metadata"] == {"_node_content": "invalid json!!", "extra": "meta"}

    @pytest.mark.asyncio
    async def test_score_none_becomes_zero(self) -> None:
        point = MagicMock()
        point.score = None
        point.payload = {"text": "no score"}
        mock_client = MagicMock()
        mock_client.query_points.return_value = MagicMock(points=[point])
        mock_embed = AsyncMock()
        mock_embed.aget_query_embedding = AsyncMock(return_value=[0.1])
        with (
            patch("src.back.rag.search.get_qdrant_client", return_value=mock_client),
            patch("src.back.rag.search._get_search_embed_model", return_value=mock_embed),
        ):
            results = await search("query")
        assert len(results) == 1
        assert results[0]["score"] == 0.0
        assert results[0]["text"] == "no score"

    @pytest.mark.asyncio
    async def test_below_threshold_excluded(self) -> None:
        point = MagicMock()
        point.score = 0.3
        point.payload = {"text": "low"}
        mock_client = MagicMock()
        mock_client.query_points.return_value = MagicMock(points=[point])
        mock_embed = AsyncMock()
        mock_embed.aget_query_embedding = AsyncMock(return_value=[0.1])
        with (
            patch("src.back.rag.search.get_qdrant_client", return_value=mock_client),
            patch("src.back.rag.search._get_search_embed_model", return_value=mock_embed),
        ):
            results = await search("query", similarity_threshold=0.5)
        assert results == []

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self) -> None:
        with patch("src.back.rag.search.get_qdrant_client", side_effect=ValueError("fail")):
            results = await search("query")
        assert results == []


class TestSearchEngineSearch:
    @pytest.mark.asyncio
    async def test_default_top_k(self) -> None:
        engine = SearchEngine()
        with patch("src.back.rag.search.search", AsyncMock(return_value=[{"text": "a"}])):
            results = await engine.search("q")
        assert len(results) == 1
        assert results[0]["text"] == "a"
        assert "rrf_score" in results[0]

    @pytest.mark.asyncio
    async def test_custom_top_k(self) -> None:
        engine = SearchEngine()
        with patch("src.back.rag.search.search", AsyncMock()) as mock_search:
            await engine.search("q", top_k=3)
        # per_collection_k = max(3 * 2, 10) = 10
        assert mock_search.call_count == len(engine.collection_names)
        for call in mock_search.call_args_list:
            assert call.kwargs["query"] == "q"
            assert call.kwargs["top_k"] == 10
            assert call.kwargs["similarity_threshold"] == 0.0


class TestFormatSearchResult:
    def test_basic_formatting(self) -> None:
        result = format_search_result(
            {
                "text": "some rule text",
                "score": 0.95,
                "metadata": {"file_path": "/path/to/rule.yaml", "line_start": 10},
            }
        )
        assert result["text"] == "some rule text"
        assert result["score"] == 0.95
        assert result["file_path"] == "/path/to/rule.yaml"
        assert result["line_number"] == 10

    def test_empty_metadata(self) -> None:
        result = format_search_result({"text": "text", "score": 0.0, "metadata": {}})
        assert result["file_path"] == ""
        assert result["line_number"] == ""


class TestGetCitation:
    def test_with_file_and_line(self) -> None:
        result = get_citation({"metadata": {"file_path": "rules/test.yaml", "line_start": "15"}})
        assert result == "rules/test.yaml:15"

    def test_with_integer_line(self) -> None:
        result = get_citation({"metadata": {"file_path": "rules/test.yaml", "line_start": 15}})
        assert result == "rules/test.yaml:15"

    def test_missing_file(self) -> None:
        result = get_citation({"metadata": {"line_start": "15"}})
        assert result == ""

    def test_missing_line(self) -> None:
        result = get_citation({"metadata": {"file_path": "rules/test.yaml"}})
        assert result == ""

    def test_empty_metadata(self) -> None:
        result = get_citation({"metadata": {}})
        assert result == ""

    def test_no_metadata(self) -> None:
        result = get_citation({})
        assert result == ""
