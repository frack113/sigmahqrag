"""Tests for RAG search functionality."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.rag.search import (
    SearchEngine,
    _get_search_embed_model,
    format_result_by_collection,
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
            patch("src.rag.search._async_embed_model", None),
            patch("src.rag.search.DatabaseService.get_instance", return_value=mock_db),
            patch("src.rag.search.build_embed_model") as mock_build,
        ):
            from src.rag.ingestion import DEFAULT_MODEL

            _get_search_embed_model()
        mock_build.assert_called_once_with(DEFAULT_MODEL)

    def test_subsequent_call_returns_cached(self) -> None:
        mock_db = MagicMock()
        mock_db.get_embedding_config.return_value = {}
        with (
            patch("src.rag.search._async_embed_model", None),
            patch("src.rag.search.DatabaseService.get_instance", return_value=mock_db),
            patch("src.rag.search.build_embed_model") as mock_build,
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
            patch("src.rag.search.get_qdrant_client", return_value=mock_client),
            patch("src.rag.search._get_search_embed_model", return_value=mock_embed),
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
            patch("src.rag.search.get_qdrant_client", return_value=mock_client),
            patch("src.rag.search._get_search_embed_model", return_value=mock_embed),
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
            patch("src.rag.search.get_qdrant_client", return_value=mock_client),
            patch("src.rag.search._get_search_embed_model", return_value=mock_embed),
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
            patch("src.rag.search.get_qdrant_client", return_value=mock_client),
            patch("src.rag.search._get_search_embed_model", return_value=mock_embed),
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
            patch("src.rag.search.get_qdrant_client", return_value=mock_client),
            patch("src.rag.search._get_search_embed_model", return_value=mock_embed),
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
            patch("src.rag.search.get_qdrant_client", return_value=mock_client),
            patch("src.rag.search._get_search_embed_model", return_value=mock_embed),
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
            patch("src.rag.search.get_qdrant_client", return_value=mock_client),
            patch("src.rag.search._get_search_embed_model", return_value=mock_embed),
        ):
            results = await search("query", similarity_threshold=0.5)
        assert results == []

    @pytest.mark.asyncio
    async def test_exception_returns_empty(self) -> None:
        with patch("src.rag.search.get_qdrant_client", side_effect=ValueError("fail")):
            results = await search("query")
        assert results == []


class TestSearchEngineSearch:
    @pytest.mark.asyncio
    async def test_default_top_k(self) -> None:
        engine = SearchEngine()
        with patch("src.rag.search.search", AsyncMock(return_value=[{"text": "a"}])):
            results = await engine.search("q")
        assert len(results) == 1
        assert results[0]["text"] == "a"
        assert "rrf_score" in results[0]

    @pytest.mark.asyncio
    async def test_custom_top_k(self) -> None:
        engine = SearchEngine()
        with patch("src.rag.search.search", AsyncMock()) as mock_search:
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


class TestFormatResultByCollection:
    def test_sigma_rules_format(self) -> None:
        result = {
            "text": "detection text",
            "score": 0.9,
            "metadata": {
                "collection": "sigma_rules",
                "source_file": "/rules/test.yml",
                "rule_id": "abc-123",
                "title": "Test Rule",
                "level": "high",
                "status": "stable",
                "chunk_type": "executive_summary",
                "product": "windows",
                "category": "process_creation",
            },
        }
        formatted = format_result_by_collection(result)
        assert formatted["collection"] == "sigma_rules"
        assert formatted["rule_id"] == "abc-123"
        assert formatted["title"] == "Test Rule"
        assert formatted["level"] == "high"
        assert formatted["chunk_type"] == "executive_summary"
        assert formatted["text"] == "detection text"
        assert formatted["score"] == 0.9

    def test_sigma_docs_format(self) -> None:
        result = {
            "text": "CVE description",
            "score": 0.85,
            "metadata": {
                "collection": "sigma_docs",
                "source_file": "/docs/cve.md",
                "doc_type": "markdown",
                "heading_text": "CVE-2024-1234",
                "heading_level": 2,
            },
        }
        formatted = format_result_by_collection(result)
        assert formatted["collection"] == "sigma_docs"
        assert formatted["doc_type"] == "markdown"
        assert formatted["heading_text"] == "CVE-2024-1234"
        assert formatted["heading_level"] == 2
        assert "rule_id" not in formatted

    def test_sigma_spec_format(self) -> None:
        result = {
            "text": "spec content",
            "score": 0.7,
            "metadata": {
                "collection": "sigma_spec",
                "source_file": "/spec/format.md",
            },
        }
        formatted = format_result_by_collection(result)
        assert formatted["collection"] == "sigma_spec"
        assert formatted["source_file"] == "/spec/format.md"
        assert "rule_id" not in formatted
        assert "heading_text" not in formatted

    def test_unknown_collection_format(self) -> None:
        result = {
            "text": "some text",
            "score": 0.5,
            "metadata": {},
        }
        formatted = format_result_by_collection(result)
        assert formatted["collection"] == ""
        assert formatted["text"] == "some text"

    def test_base_fields_always_present(self) -> None:
        result = {
            "text": "text",
            "score": 0.9,
            "metadata": {"collection": "sigma_rules"},
        }
        formatted = format_result_by_collection(result)
        assert "text" in formatted
        assert "score" in formatted
        assert "collection" in formatted
        assert "source_file" in formatted


class TestSearchEngineWithRouter:
    def test_init_use_router_default_false(self) -> None:
        engine = SearchEngine()
        assert engine.use_router is False

    def test_init_use_router_true(self) -> None:
        engine = SearchEngine(use_router=True)
        assert engine.use_router is True

    @pytest.mark.asyncio
    async def test_router_disabled_searches_all_collections(self) -> None:
        engine = SearchEngine(use_router=False)
        with patch("src.rag.search.search", AsyncMock(return_value=[{"text": "a"}])) as mock_search:
            await engine.search("q")
        assert mock_search.call_count == 3

    @pytest.mark.asyncio
    async def test_router_enabled_filters_collections(self) -> None:
        engine = SearchEngine(use_router=True)
        with (
            patch("src.rag.search.route_query", AsyncMock(return_value=["sigma_rules"])),
            patch("src.rag.search.search", AsyncMock(return_value=[{"text": "a"}])) as mock_search,
        ):
            await engine.search("q")
        assert mock_search.call_count == 1
        assert mock_search.call_args_list[0].kwargs["collection_name"] == "sigma_rules"

    @pytest.mark.asyncio
    async def test_router_returns_unknown_collection_falls_back(self) -> None:
        engine = SearchEngine(use_router=True)
        with (
            patch(
                "src.rag.search.route_query",
                AsyncMock(return_value=["unknown_collection"]),
            ),
            patch("src.rag.search.search", AsyncMock(return_value=[{"text": "a"}])) as mock_search,
        ):
            await engine.search("q")
        # Falls back to all collections when routed results don't match
        assert mock_search.call_count == 3

    @pytest.mark.asyncio
    async def test_router_failure_falls_back(self) -> None:
        engine = SearchEngine(use_router=True)
        with (
            patch("src.rag.search.route_query", AsyncMock(side_effect=Exception("timeout"))),
            patch("src.rag.search.search", AsyncMock(return_value=[{"text": "a"}])) as mock_search,
        ):
            await engine.search("q")
        assert mock_search.call_count == 3
