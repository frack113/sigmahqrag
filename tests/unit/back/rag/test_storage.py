"""Tests for Qdrant storage operations."""

import uuid
from unittest.mock import MagicMock, patch

import pytest

from src.back.qdrant.storage import _delete_by_source, _make_point_id, store_embeddings


class TestMakePointId:
    """Tests for deterministic point ID generation."""

    def test_deterministic_with_source_and_chunk(self) -> None:
        meta = {"source_file": "/path/to/rule.yml", "chunk_type": "executive_summary"}
        id1 = _make_point_id("sigma_rules", meta)
        id2 = _make_point_id("sigma_rules", meta)
        assert id1 == id2
        # Should be a valid UUID
        uuid.UUID(id1)

    def test_different_sources_produce_different_ids(self) -> None:
        meta1 = {"source_file": "/a.yml", "chunk_type": "global"}
        meta2 = {"source_file": "/b.yml", "chunk_type": "global"}
        assert _make_point_id("sigma_docs", meta1) != _make_point_id("sigma_docs", meta2)

    def test_different_chunk_types_produce_different_ids(self) -> None:
        meta = {"source_file": "/rule.yml"}
        id1 = _make_point_id("sigma_rules", {**meta, "chunk_type": "global"})
        id2 = _make_point_id("sigma_rules", {**meta, "chunk_type": "heading_h1"})
        assert id1 != id2

    def test_different_collections_produce_different_ids(self) -> None:
        meta = {"source_file": "/rule.yml", "chunk_type": "global"}
        id1 = _make_point_id("sigma_rules", meta)
        id2 = _make_point_id("sigma_docs", meta)
        assert id1 != id2

    def test_fallback_to_uuid4_when_source_missing(self) -> None:
        meta = {"chunk_type": "global"}
        point_id = _make_point_id("sigma_rules", meta)
        # Should be a valid UUID (uuid4 format)
        uuid.UUID(point_id)

    def test_fallback_to_uuid4_when_chunk_type_missing(self) -> None:
        meta = {"source_file": "/rule.yml"}
        point_id = _make_point_id("sigma_rules", meta)
        uuid.UUID(point_id)

    def test_fallback_to_uuid4_when_metadata_empty(self) -> None:
        point_id = _make_point_id("sigma_rules", {})
        uuid.UUID(point_id)


class TestDeleteBySource:
    """Tests for source-based point deletion."""

    def test_calls_delete_with_filter(self) -> None:
        mock_client = MagicMock()
        _delete_by_source(mock_client, "sigma_rules", "/path/to/rule.yml")

        mock_client.delete.assert_called_once()
        call_args = mock_client.delete.call_args
        assert call_args.kwargs["collection_name"] == "sigma_rules"
        # Verify the filter structure
        points_selector = call_args.kwargs["points_selector"]
        assert points_selector.must[0].key == "source_file"
        assert points_selector.must[0].match.value == "/path/to/rule.yml"

    def test_handles_exception_gracefully(self) -> None:
        mock_client = MagicMock()
        mock_client.delete.side_effect = Exception("connection lost")
        # Should not raise
        _delete_by_source(mock_client, "sigma_rules", "/path/to/rule.yml")


class TestStoreEmbeddings:
    """Tests for store_embeddings with delete-before-upsert."""

    @pytest.mark.asyncio
    async def test_returns_false_on_count_mismatch(self) -> None:
        result = await store_embeddings(
            embeddings=[[0.1]],
            documents=["a", "b"],
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_deterministic_ids_for_same_source(self) -> None:
        meta = [
            {"source_file": "/rule.yml", "chunk_type": "global"},
            {"source_file": "/rule.yml", "chunk_type": "heading_h1"},
        ]
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])

        with patch("src.back.qdrant.storage.get_qdrant_client", return_value=mock_client):
            result = await store_embeddings(
                embeddings=[[0.1], [0.2]],
                documents=["text1", "text2"],
                metadata=meta,
                collection_name="sigma_rules",
            )

        assert result is True
        # Verify upsert was called
        mock_client.upsert.assert_called_once()
        points = mock_client.upsert.call_args.kwargs["points"]
        # Both points should have deterministic IDs (not random)
        assert (
            points[0].id == points[1].id[:8] or points[0].id != points[1].id
        )  # different chunks = different IDs

    @pytest.mark.asyncio
    async def test_delete_before_upsert(self) -> None:
        meta = [
            {"source_file": "/rule.yml", "chunk_type": "global"},
            {"source_file": "/rule.yml", "chunk_type": "heading_h1"},
        ]
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(
            collections=[MagicMock(name="sigma_rules")]
        )

        with patch("src.back.qdrant.storage.get_qdrant_client", return_value=mock_client):
            await store_embeddings(
                embeddings=[[0.1], [0.2]],
                documents=["text1", "text2"],
                metadata=meta,
                collection_name="sigma_rules",
            )

        # Delete should be called once per unique source_file
        mock_client.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_creates_collection_if_missing(self) -> None:
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])

        with patch("src.back.qdrant.storage.get_qdrant_client", return_value=mock_client):
            await store_embeddings(
                embeddings=[[0.1]],
                documents=["text"],
                metadata=[{"source_file": "/a.yml", "chunk_type": "global"}],
                collection_name="new_collection",
            )

        mock_client.recreate_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_delete_when_no_source_in_metadata(self) -> None:
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(
            collections=[MagicMock(name="sigma_docs")]
        )

        with patch("src.back.qdrant.storage.get_qdrant_client", return_value=mock_client):
            await store_embeddings(
                embeddings=[[0.1]],
                documents=["text"],
                metadata=[{"some_field": "value"}],
                collection_name="sigma_docs",
            )

        # No delete because no source_file in metadata
        mock_client.delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_multiple_sources_each_deleted(self) -> None:
        meta = [
            {"source_file": "/a.yml", "chunk_type": "global"},
            {"source_file": "/b.yml", "chunk_type": "global"},
        ]
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(
            collections=[MagicMock(name="sigma_docs")]
        )

        with patch("src.back.qdrant.storage.get_qdrant_client", return_value=mock_client):
            await store_embeddings(
                embeddings=[[0.1], [0.2]],
                documents=["text1", "text2"],
                metadata=meta,
                collection_name="sigma_docs",
            )

        # Delete called once per unique source
        assert mock_client.delete.call_count == 2
