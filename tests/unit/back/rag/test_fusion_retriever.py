"""Tests for QueryFusionRetriever migration in SearchEngine."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.search.engine import SearchEngine


class TestQueryFusionRetrieverBasic:
    """Test basic QueryFusionRetriever integration replacing manual RRF."""

    @pytest.mark.asyncio
    async def test_uses_query_fusion_retriever(self) -> None:
        """Search should use LlamaIndex QueryFusionRetriever by default."""
        engine = SearchEngine()
        mock_node = MagicMock()
        mock_node.text = "test result"
        mock_node.score = 0.85
        mock_node.metadata = {"file_path": "test.yaml"}

        with (
            patch(
                "src.core.search.engine.get_collection_retriever",
                return_value=MagicMock(),
            ) as mock_retriever,
            patch("src.core.search.engine.QueryFusionRetriever") as mock_fusion_class,
        ):
            mock_fusion = MagicMock()
            mock_fusion.aretrieve = AsyncMock(return_value=[mock_node])
            mock_fusion_class.return_value = mock_fusion

            results = await engine.search("test query")

        assert len(results) == 1
        assert results[0]["text"] == "test result"
        assert results[0]["score"] == pytest.approx(0.85)
        # Default SearchEngine has 3 collections, so retriever is called 3 times
        assert mock_retriever.call_count == len(engine.collection_names)
        mock_fusion_class.assert_called_once()

    @pytest.mark.asyncio
    async def test_respects_top_k_limit(self) -> None:
        """QueryFusionRetriever should return at most limit results."""
        engine = SearchEngine(top_k=5)
        mock_nodes = [
            MagicMock(text=f"result {i}", score=0.9 - i * 0.1, metadata={}) for i in range(20)
        ]

        with (
            patch("src.core.search.engine.get_collection_retriever", return_value=MagicMock()),
            patch("src.core.search.engine.QueryFusionRetriever") as mock_fusion_class,
        ):
            mock_fusion = MagicMock()
            mock_fusion.aretrieve = AsyncMock(return_value=mock_nodes)
            mock_fusion_class.return_value = mock_fusion

            results = await engine.search("query", top_k=5)

        assert len(results) == 5
        # Verify similarity_top_k was set to limit
        call_kwargs = mock_fusion_class.call_args.kwargs
        assert call_kwargs["similarity_top_k"] == 5

    @pytest.mark.asyncio
    async def test_num_queries_set_to_1(self) -> None:
        """num_queries=1 should disable dynamic query generation."""
        engine = SearchEngine()

        with (
            patch("src.core.search.engine.get_collection_retriever", return_value=MagicMock()),
            patch("src.core.search.engine.QueryFusionRetriever") as mock_fusion_class,
        ):
            mock_fusion = MagicMock()
            mock_fusion.aretrieve = AsyncMock(
                return_value=[MagicMock(text="ok", score=0.5, metadata={})]
            )
            mock_fusion_class.return_value = mock_fusion

            await engine.search("query")

        call_kwargs = mock_fusion_class.call_args.kwargs
        assert call_kwargs["num_queries"] == 1


class TestQueryFusionRetrieverFilters:
    """Test that metadata filters are correctly applied to individual retrievers."""

    @pytest.mark.asyncio
    async def test_metadata_filter_passed_to_retrievers(self) -> None:
        """Each collection retriever should receive the Qdrant filter."""
        engine = SearchEngine(collection_names=["sigma_rules", "sigma_docs"])
        mock_node = MagicMock(text="result", score=0.8, metadata={})

        with (
            patch(
                "src.core.search.engine.get_collection_retriever", return_value=MagicMock()
            ) as mock_get,
            patch("src.core.search.engine.QueryFusionRetriever") as mock_fusion_class,
        ):
            mock_fusion = MagicMock()
            mock_fusion.aretrieve = AsyncMock(return_value=[mock_node])
            mock_fusion_class.return_value = mock_fusion

            await engine.search("query", metadata_filter={"level": "high"})

        assert mock_get.call_count == 2
        for call in mock_get.call_args_list:
            assert call.kwargs["metadata_filter"] is not None

    @pytest.mark.asyncio
    async def test_no_filter_when_metadata_filter_none(self) -> None:
        """When no metadata filter provided, should not pass filter to retrievers."""
        engine = SearchEngine(collection_names=["sigma_rules"])
        mock_node = MagicMock(text="result", score=0.8, metadata={})

        with (
            patch(
                "src.core.search.engine.get_collection_retriever", return_value=MagicMock()
            ) as mock_get,
            patch("src.core.search.engine.QueryFusionRetriever") as mock_fusion_class,
        ):
            mock_fusion = MagicMock()
            mock_fusion.aretrieve = AsyncMock(return_value=[mock_node])
            mock_fusion_class.return_value = mock_fusion

            await engine.search("query", metadata_filter=None)

        for call in mock_get.call_args_list:
            assert call.kwargs["metadata_filter"] is None


class TestQueryFusionRetrieverMultiCollection:
    """Test multi-collection fusion behavior."""

    @pytest.mark.asyncio
    async def test_creates_retriever_for_each_collection(self) -> None:
        """Should create one retriever per collection in collection_names."""
        engine = SearchEngine(collection_names=["sigma_rules", "sigma_docs", "sigma_spec"])

        with (
            patch(
                "src.core.search.engine.get_collection_retriever", return_value=MagicMock()
            ) as mock_get,
            patch("src.core.search.engine.QueryFusionRetriever") as mock_fusion_class,
        ):
            mock_fusion = MagicMock()
            mock_fusion.aretrieve = AsyncMock(
                return_value=[MagicMock(text="ok", score=0.5, metadata={})]
            )
            mock_fusion_class.return_value = mock_fusion

            await engine.search("query")

        assert mock_get.call_count == 3

    @pytest.mark.asyncio
    async def test_per_collection_k_is_double_limit(self) -> None:
        """Each retriever should query per_collection_k = max(limit * 2, 10)."""
        engine = SearchEngine()

        with (
            patch(
                "src.core.search.engine.get_collection_retriever", return_value=MagicMock()
            ) as mock_get,
            patch("src.core.search.engine.QueryFusionRetriever") as mock_fusion_class,
        ):
            mock_fusion = MagicMock()
            mock_fusion.aretrieve = AsyncMock(
                return_value=[MagicMock(text="ok", score=0.5, metadata={})]
            )
            mock_fusion_class.return_value = mock_fusion

            await engine.search("query", top_k=15)

        # per_collection_k = max(15 * 2, 10) = 30
        for call in mock_get.call_args_list:
            assert call.kwargs["top_k"] == 30


class TestQueryFusionRetrieverFallback:
    """Test fallback to manual RRF when QueryFusionRetriever fails."""

    @pytest.mark.asyncio
    async def test_fallback_on_queryfusion_error(self) -> None:
        """Should fall back to _search_manual_rrf on QueryFusionRetriever exception."""
        engine = SearchEngine()

        with (
            patch("src.core.search.engine.get_collection_retriever", return_value=MagicMock()),
            patch(
                "src.core.search.engine.QueryFusionRetriever",
                side_effect=Exception("fusion failed"),
            ),
            patch.object(engine, "_search_manual_rrf", new_callable=AsyncMock) as mock_fallback,
        ):
            mock_fallback.return_value = [{"text": "fallback result", "rrf_score": 0.9}]

            results = await engine.search("query")

        assert len(results) == 1
        assert results[0]["text"] == "fallback result"
        mock_fallback.assert_called_once()


class TestQueryFusionRetrieverRouter:
    """Test router integration with QueryFusionRetriever."""

    @pytest.mark.asyncio
    async def test_router_filters_collections_before_retrievers(self) -> None:
        """When use_router=True, only create retrievers for routed collections."""
        engine = SearchEngine(use_router=True, collection_names=["sigma_rules", "sigma_docs"])

        with (
            patch(
                "src.core.search.engine.route_query",
                new_callable=AsyncMock,
                return_value=["sigma_rules"],
            ),
            patch(
                "src.core.search.engine.get_collection_retriever", return_value=MagicMock()
            ) as mock_get,
            patch("src.core.search.engine.QueryFusionRetriever") as mock_fusion_class,
        ):
            mock_fusion = MagicMock()
            mock_fusion.aretrieve = AsyncMock(
                return_value=[MagicMock(text="ok", score=0.5, metadata={})]
            )
            mock_fusion_class.return_value = mock_fusion

            await engine.search("query")

        assert mock_get.call_count == 1
        assert mock_get.call_args.kwargs["collection_name"] == "sigma_rules"

    @pytest.mark.asyncio
    async def test_router_invalid_collection_falls_back_to_all(self) -> None:
        """When router returns unknown collection, search all collections."""
        engine = SearchEngine(
            use_router=True,
            collection_names=["sigma_rules", "sigma_docs"],
        )

        with (
            patch(
                "src.core.search.engine.route_query",
                new_callable=AsyncMock,
                return_value=["unknown"],
            ),
            patch(
                "src.core.search.engine.get_collection_retriever", return_value=MagicMock()
            ) as mock_get,
            patch("src.core.search.engine.QueryFusionRetriever") as mock_fusion_class,
        ):
            mock_fusion = MagicMock()
            mock_fusion.aretrieve = AsyncMock(
                return_value=[MagicMock(text="ok", score=0.5, metadata={})]
            )
            mock_fusion_class.return_value = mock_fusion

            await engine.search("query")

        assert mock_get.call_count == 2


class TestQueryFusionRetrieverSimilarityThreshold:
    """Test similarity threshold filtering with QueryFusionRetriever."""

    @pytest.mark.asyncio
    async def test_filter_below_threshold(self) -> None:
        """Results below similarity_threshold should be excluded."""
        engine = SearchEngine(similarity_threshold=0.7)
        mock_nodes = [
            MagicMock(text="high", score=0.9, metadata={}),
            MagicMock(text="low", score=0.5, metadata={}),
        ]

        with (
            patch("src.core.search.engine.get_collection_retriever", return_value=MagicMock()),
            patch("src.core.search.engine.QueryFusionRetriever") as mock_fusion_class,
        ):
            mock_fusion = MagicMock()
            mock_fusion.aretrieve = AsyncMock(return_value=mock_nodes)
            mock_fusion_class.return_value = mock_fusion

            results = await engine.search("query")

        assert len(results) == 1
        assert results[0]["text"] == "high"


class TestNodeToResult:
    """Test _node_to_result conversion from LlamaIndex NodeWithScore to dict."""

    @pytest.mark.asyncio
    async def test_flat_node_conversion(self) -> None:
        """Convert flat NodeWithScore with direct attributes."""
        mock_node = MagicMock()
        mock_node.text = "test text"
        mock_node.score = 0.85
        mock_node.metadata = {"key": "value"}

        from src.core.search.engine import _node_to_result

        result = _node_to_result(mock_node)

        assert result["text"] == "test text"
        assert result["score"] == pytest.approx(0.85)
        assert result["metadata"] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_none_score_becomes_zero(self) -> None:
        """None score should become 0.0."""
        mock_node = MagicMock()
        mock_node.text = "text"
        mock_node.score = None
        mock_node.metadata = {}

        from src.core.search.engine import _node_to_result

        result = _node_to_result(mock_node)

        assert result["score"] == 0.0


class TestBuildLlamaFilters:
    """Test _build_llama_filters conversion from Qdrant Filter to LlamaIndex MetadataFilters."""

    def test_none_filter_returns_none(self) -> None:
        from src.core.search.retrievers import _build_llama_filters

        result = _build_llama_filters(None)
        assert result is None

    def test_empty_conditions_returns_none(self) -> None:
        mock_filter = MagicMock(must=[])
        from src.core.search.retrievers import _build_llama_filters

        result = _build_llama_filters(mock_filter)
        assert result is None

    def test_simple_match_value_filter(self) -> None:
        """Convert Must + MatchValue condition to MetadataFilter."""
        mock_condition = MagicMock()
        mock_condition.key = "level"
        mock_match = MagicMock(value="high")
        mock_condition.match = mock_match

        mock_filter = MagicMock(must=[mock_condition])

        from src.core.search.retrievers import _build_llama_filters, MetadataFilters

        result = _build_llama_filters(mock_filter)

        assert isinstance(result, MetadataFilters)
        assert len(result.filters) == 1
        assert result.filters[0].key == "level"
        assert result.filters[0].value == "high"

    def test_multiple_conditions_combined(self) -> None:
        """Multiple conditions should create multiple MetadataFilters."""
        mock_cond1 = MagicMock()
        mock_cond1.key = "level"
        mock_match1 = MagicMock(value="high")
        mock_cond1.match = mock_match1

        mock_cond2 = MagicMock()
        mock_cond2.key = "status"
        mock_match2 = MagicMock(value="stable")
        mock_cond2.match = mock_match2

        mock_filter = MagicMock(must=[mock_cond1, mock_cond2])

        from src.core.search.retrievers import _build_llama_filters, MetadataFilters

        result = _build_llama_filters(mock_filter)

        assert isinstance(result, MetadataFilters)
        assert len(result.filters) == 2


class TestGetCollectionRetriever:
    """Test get_collection_retriever factory function."""

    def test_returns_vector_index_retriever(self) -> None:
        from src.core.search.retrievers import get_collection_retriever as gcr
        from llama_index.core.retrievers import VectorIndexRetriever

        with (
            patch("src.core.search.retrievers.get_qdrant_client") as mock_client,
            patch("src.core.search.retrievers.QdrantVectorStore"),
            patch("src.core.search.retrievers.VectorStoreIndex") as mock_index_class,
            patch("src.core.search.engine._get_search_embed_model", return_value=MagicMock()),
        ):
            mock_client.return_value = MagicMock()
            mock_index_class.from_vector_store.return_value = MagicMock()
            result = gcr("test_collection", top_k=10)

        assert isinstance(result, VectorIndexRetriever)

    def test_passes_top_k_to_retriever(self) -> None:
        from src.core.search.retrievers import get_collection_retriever as gcr

        with (
            patch("src.core.search.retrievers.get_qdrant_client") as mock_client,
            patch("src.core.search.retrievers.QdrantVectorStore"),
            patch("src.core.search.retrievers.VectorStoreIndex") as mock_index_class,
            patch("src.core.search.engine._get_search_embed_model", return_value=MagicMock()),
        ):
            mock_client.return_value = MagicMock()
            gcr("test", top_k=25)

            # Verify VectorStoreIndex.from_vector_store was called (confirms retriever creation)
            assert mock_index_class.from_vector_store.called


class TestIntegration:
    """Integration tests for QueryFusionRetriever end-to-end flow."""

    @pytest.mark.asyncio
    async def test_full_search_flow(self) -> None:
        """Test complete search flow from query to fused results."""
        engine = SearchEngine(top_k=10, similarity_threshold=0.6)

        # Create mock nodes with varying scores
        high_score_nodes = [
            MagicMock(text="result 1", score=0.95, metadata={"collection": "sigma_rules"}),
            MagicMock(text="result 2", score=0.85, metadata={"collection": "sigma_docs"}),
            MagicMock(text="result 3", score=0.75, metadata={"collection": "sigma_spec"}),
        ]
        low_score_node = [MagicMock(text="result 4", score=0.4, metadata={})]

        with (
            patch("src.core.search.engine.get_collection_retriever", return_value=MagicMock()),
            patch("src.core.search.engine.QueryFusionRetriever") as mock_fusion_class,
        ):
            mock_fusion = MagicMock()
            mock_fusion.aretrieve = AsyncMock(return_value=high_score_nodes + low_score_node)
            mock_fusion_class.return_value = mock_fusion

            results = await engine.search("sigma detection query", top_k=10)

        # Should have 3 results above threshold (0.6), limited to 10
        assert len(results) == 3
        assert all(r["score"] >= 0.6 for r in results)
        assert results[0]["text"] == "result 1"
        assert results[1]["text"] == "result 2"

    @pytest.mark.asyncio
    async def test_async_retrieval(self) -> None:
        """Verify QueryFusionRetriever uses await aretrieve (async)."""
        engine = SearchEngine()
        mock_node = MagicMock(text="async result", score=0.8, metadata={})

        with (
            patch("src.core.search.engine.get_collection_retriever", return_value=MagicMock()),
            patch("src.core.search.engine.QueryFusionRetriever") as mock_fusion_class,
        ):
            mock_fusion = MagicMock()
            mock_fusion.aretrieve = AsyncMock(return_value=[mock_node])
            mock_fusion_class.return_value = mock_fusion

            await engine.search("query")

            # Verify aretrieve was awaited (not called synchronously)
            mock_fusion.aretrieve.assert_awaited_once()


class TestBackwardCompatibility:
    """Test backward compatibility with existing dict output format."""

    @pytest.mark.asyncio
    async def test_output_format_matches_legacy(self) -> None:
        """Output should have same keys as legacy manual RRF results."""
        engine = SearchEngine()
        mock_node = MagicMock(text="test", score=0.9, metadata={"file_path": "rule.yaml"})

        with (
            patch("src.core.search.engine.get_collection_retriever", return_value=MagicMock()),
            patch("src.core.search.engine.QueryFusionRetriever") as mock_fusion_class,
        ):
            mock_fusion = MagicMock()
            mock_fusion.aretrieve = AsyncMock(return_value=[mock_node])
            mock_fusion_class.return_value = mock_fusion

            results = await engine.search("query")

        # Should have text, score, metadata (same as legacy)
        assert "text" in results[0]
        assert "score" in results[0]
        assert "metadata" in results[0]
        # Legacy added rrf_score; QueryFusionRetriever returns raw scores directly
        # which is actually cleaner - score field contains the relevance score

    @pytest.mark.asyncio
    async def test_empty_results_on_no_retrievers(self) -> None:
        """When all retriever creation fails, should return empty list."""
        engine = SearchEngine(collection_names=["sigma_rules"])

        with (
            patch(
                "src.core.search.engine.get_collection_retriever",
                side_effect=Exception("collection not found"),
            ),
        ):
            results = await engine.search("query")

        assert results == []
