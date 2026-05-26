"""Tests for Qdrant collection management."""

from unittest.mock import MagicMock


from src.back.qdrant.collections import (
    _count_sync,
    _create_collection_sync,
    _delete_collection_sync,
    _get_collection_sync,
    _get_collections_sync,
)


class TestSyncWrappers:
    def test_get_collections_sync(self) -> None:
        client = MagicMock()
        _get_collections_sync(client)
        client.get_collections.assert_called_once()

    def test_get_collection_sync(self) -> None:
        client = MagicMock()
        _get_collection_sync(client, "test-collection")
        client.get_collection.assert_called_once_with(collection_name="test-collection")

    def test_count_sync(self) -> None:
        client = MagicMock()
        client.count.return_value.count = 42
        result = _count_sync(client, "test-collection")
        assert result == 42
        client.count.assert_called_once_with(collection_name="test-collection")

    def test_create_collection_sync(self) -> None:
        client = MagicMock()
        vectors_config = MagicMock()
        _create_collection_sync(client, "test-collection", vectors_config)
        client.create_collection.assert_called_once_with(
            collection_name="test-collection",
            vectors_config=vectors_config,
        )

    def test_delete_collection_sync(self) -> None:
        client = MagicMock()
        _delete_collection_sync(client, "test-collection")
        client.delete_collection.assert_called_once_with(collection_name="test-collection")
