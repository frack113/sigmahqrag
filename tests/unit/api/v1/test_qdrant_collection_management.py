from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.api.v1.qdrant import router
from fastapi import FastAPI
import pytest

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.mark.asyncio
async def test_list_collections():
    with patch("src.api.v1.qdrant.list_collections", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [{"name": "test_collection"}]
        response = client.post(
            "/api/v1/qdrant",
            json={
                "action": "collection_management",
                "payload": {"action": "collection_management", "operation": "list"},
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["data"][0]["name"] == "test_collection"


@pytest.mark.asyncio
async def test_create_collection():
    with patch("src.api.v1.qdrant.create_collection", new_callable=AsyncMock) as mock_create:
        response = client.post(
            "/api/v1/qdrant",
            json={
                "action": "collection_management",
                "payload": {
                    "action": "collection_management",
                    "operation": "create",
                    "collection_name": "new_col",
                    "config": {"vector_size": 384},
                },
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert "new_col created" in response.json()["message"]
        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_delete_collection():
    with patch("src.api.v1.qdrant.delete_collection", new_callable=AsyncMock) as mock_delete:
        response = client.post(
            "/api/v1/qdrant",
            json={
                "action": "collection_management",
                "payload": {
                    "action": "collection_management",
                    "operation": "delete",
                    "collection_name": "old_col",
                },
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert "old_col deleted" in response.json()["message"]
        mock_delete.assert_called_once()


@pytest.mark.asyncio
async def test_get_collection():
    with patch("src.api.v1.qdrant.get_collection", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"name": "test_col", "status": "active"}
        response = client.post(
            "/api/v1/qdrant",
            json={
                "action": "collection_management",
                "payload": {
                    "action": "collection_management",
                    "operation": "get",
                    "collection_name": "test_col",
                },
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["data"]["name"] == "test_col"


@pytest.mark.asyncio
async def test_create_collection_exists():
    with patch("src.api.v1.qdrant.get_collection", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"name": "test_col", "status": "active"}
        response = client.post(
            "/api/v1/qdrant",
            json={
                "action": "collection_management",
                "payload": {
                    "action": "collection_management",
                    "operation": "get",
                    "collection_name": "test_col",
                },
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["data"]["name"] == "test_col"
