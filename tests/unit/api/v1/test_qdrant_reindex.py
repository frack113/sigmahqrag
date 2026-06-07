"""Tests for qdrant.py reindex handler."""

from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI
import pytest

from src.api.v1.qdrant import router

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_db():
    db = MagicMock()
    db.reset_embed_status_for_collection.return_value = None
    with patch("src.api.v1.qdrant.DatabaseService.get_instance", return_value=db):
        yield db


@pytest.mark.asyncio
async def test_reindex_unknown_collection(mock_db):
    response = client.post(
        "/api/v1/qdrant",
        json={
            "action": "reindex",
            "payload": {"action": "reindex", "collection_name": "nonexistent"},
        },
    )
    data = response.json()
    assert data["status"] == "error"
    assert data["error_code"] == "UNKNOWN_COLLECTION"


@pytest.mark.asyncio
async def test_reindex_sigma_spec(mock_db):
    mock_db._writer_conn = MagicMock()

    with (
        patch("src.infrastructure.vectorstore.client.get_qdrant_client") as mock_qc,
        patch("src.api.v1.qdrant._recreate_collection"),
        patch("src.api.v1.qdrant.UnifiedIndexer") as mock_indexer_cls,
    ):
        mock_client = MagicMock()
        mock_qc.return_value = mock_client

        mock_indexer = MagicMock()
        mock_result = MagicMock()
        mock_result.route.qdrant_collection = "sigma_spec"
        mock_result.processed = 6
        mock_result.errors = []
        mock_indexer.index = AsyncMock(return_value=mock_result)
        mock_indexer_cls.return_value = mock_indexer

        response = client.post(
            "/api/v1/qdrant",
            json={
                "action": "reindex",
                "payload": {"action": "reindex", "collection_name": "sigma_spec"},
            },
        )
        data = response.json()
        assert data["status"] == "success"
        assert data["data"]["processed"] == 6
        mock_indexer.index.assert_called_once()


@pytest.mark.asyncio
async def test_reindex_deletes_and_recreates_collection(mock_db):
    mock_db._writer_conn = MagicMock()

    with (
        patch("src.infrastructure.vectorstore.client.get_qdrant_client") as mock_qc,
        patch("src.api.v1.qdrant._recreate_collection") as mock_recreate,
        patch("src.api.v1.qdrant.UnifiedIndexer") as mock_indexer_cls,
    ):
        mock_client = MagicMock()
        mock_qc.return_value = mock_client

        mock_indexer = MagicMock()
        mock_result = MagicMock()
        mock_result.route.qdrant_collection = "sigma_spec"
        mock_result.processed = 0
        mock_result.errors = []
        mock_indexer.index = AsyncMock(return_value=mock_result)
        mock_indexer_cls.return_value = mock_indexer

        client.post(
            "/api/v1/qdrant",
            json={
                "action": "reindex",
                "payload": {"action": "reindex", "collection_name": "sigma_spec"},
            },
        )

        mock_client.delete_collection.assert_called_once_with(collection_name="sigma_spec")
        mock_recreate.assert_called_once()
