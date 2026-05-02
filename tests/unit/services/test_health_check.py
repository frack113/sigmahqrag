import pytest
import httpx
from unittest.mock import patch, Mock
from src.services.health_check import HealthCheckService

@pytest.fixture
def health_service():
    return HealthCheckService()

@pytest.mark.asyncio
async def test_check_all_llm_success(health_service):
    with patch('httpx.get') as mock_get, \
         patch('qdrant_client.QdrantClient') as mock_qdrant_cls:
        mock_get.return_value = Mock(status_code=200)
        mock_client = Mock()
        mock_client.get_collections.return_value.collections = []
        mock_qdrant_cls.return_value = mock_client
        result = await health_service.check_all()
        assert result["llm"]["status"] == "ok"

@pytest.mark.asyncio
async def test_check_all_llm_failure(health_service):
    with patch('httpx.get') as mock_get, \
         patch('qdrant_client.QdrantClient') as mock_qdrant_cls:
        mock_get.side_effect = httpx.ConnectError("Connection refused")
        mock_client = Mock()
        mock_client.get_collections.return_value.collections = []
        mock_qdrant_cls.return_value = mock_client
        result = await health_service.check_all()
        assert result["llm"]["status"] == "error"

@pytest.mark.asyncio
async def test_check_all_qdrant_success(health_service):
    with patch('httpx.get') as mock_get, \
         patch('qdrant_client.QdrantClient') as mock_qdrant_cls, \
         patch('src.services.health_check.load_config') as mock_load_config:
        mock_get.return_value = Mock(status_code=200)
        mock_client = Mock()
        # Mock config to return known collection name
        mock_load_config.return_value = {
            "services": {
                "qdrant": {
                    "collection_name": "sigma_rules"
                }
            }
        }
        mock_client.get_collections.return_value.collections = [Mock(name="sigma_rules")]
        mock_qdrant_cls.return_value = mock_client
        result = await health_service.check_all()
        assert result["qdrant"]["status"] == "ok"

@pytest.mark.asyncio
async def test_check_all_qdrant_failure(health_service):
    with patch('httpx.get') as mock_get, \
         patch('qdrant_client.QdrantClient') as mock_qdrant_cls:
        mock_get.return_value = Mock(status_code=200)
        mock_qdrant_cls.side_effect = Exception("Connection refused")
        result = await health_service.check_all()
        assert result["qdrant"]["status"] == "error"

@pytest.mark.asyncio
async def test_check_all_caching(health_service):
    with patch('httpx.get') as mock_get, \
         patch('qdrant_client.QdrantClient') as mock_qdrant_cls, \
         patch('time.time') as mock_time:
        mock_get.return_value = Mock(status_code=200)
        mock_client = Mock()
        mock_client.get_collections.return_value.collections = []
        mock_qdrant_cls.return_value = mock_client
        mock_time.return_value = 1000.0
        result1 = await health_service.check_all()
        mock_time.return_value = 1000.0  # Same time = cache hit
        result2 = await health_service.check_all()
        assert result1["llm"] == result2["llm"]
        assert result1["qdrant"] == result2["qdrant"]
        assert mock_get.call_count == 1
