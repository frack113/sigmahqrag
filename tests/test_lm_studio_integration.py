"""
Tests for LM Studio integration and API calls.
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
import aiohttp

from src.infrastructure.external.lm_studio_client import LMStudioClient
from src.core.llm_service import LLMService


class TestLMStudioClient:
    """Test cases for LM Studio client."""
    
    @pytest.fixture
    def lm_studio_client(self):
        """Create an LM Studio client for testing."""
        return LMStudioClient(
            base_url="http://localhost:1234",
            api_key="test-key",
            timeout=30
        )
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, lm_studio_client):
        """Test LM Studio client initialization."""
        assert lm_studio_client.base_url == "http://localhost:1234"
        assert lm_studio_client.api_key == "test-key"
        assert lm_studio_client.timeout == 30
        assert lm_studio_client.session is None
    
    @pytest.mark.asyncio
    async def test_get_models_success(self, lm_studio_client):
        """Test successful model listing."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "data": [
                {"id": "model1", "object": "model"},
                {"id": "model2", "object": "model"}
            ]
        })
        mock_response.raise_for_status = Mock()
        
        with patch('aiohttp.ClientSession.get', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
            models = await lm_studio_client.get_models()
        
        assert len(models) == 2
        assert models[0]["id"] == "model1"
        assert models[1]["id"] == "model2"
    
    @pytest.mark.asyncio
    async def test_get_models_failure(self, lm_studio_client):
        """Test model listing failure."""
        with patch('aiohttp.ClientSession.get', side_effect=Exception("Connection failed")):
            models = await lm_studio_client.get_models()
        
        assert models == []
    
    @pytest.mark.asyncio
    async def test_chat_completion_success(self, lm_studio_client):
        """Test successful chat completion."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "choices": [{"message": {"content": "Test response"}}]
        })
        mock_response.raise_for_status = Mock()
        
        with patch('aiohttp.ClientSession.post', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
            response = await lm_studio_client.chat_completion(
                model="test-model",
                messages=[{"role": "user", "content": "Hello"}],
                temperature=0.7
            )
        
        assert response == "Test response"
    
    @pytest.mark.asyncio
    async def test_chat_completion_timeout(self, lm_studio_client):
        """Test chat completion timeout."""
        with patch('aiohttp.ClientSession.post', side_effect=asyncio.TimeoutError()):
            response = await lm_studio_client.chat_completion(
                model="test-model",
                messages=[{"role": "user", "content": "Hello"}]
            )
        
        assert response == "Error: Request timed out"
    
    @pytest.mark.asyncio
    async def test_chat_completion_http_error(self, lm_studio_client):
        """Test chat completion HTTP error."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock(side_effect=aiohttp.ClientResponseError(
            request_info=Mock(), history=Mock(), status=500, message="Internal Server Error"
        ))
        
        with patch('aiohttp.ClientSession.post', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
            response = await lm_studio_client.chat_completion(
                model="test-model",
                messages=[{"role": "user", "content": "Hello"}]
            )
        
        assert "Error" in response
    
    @pytest.mark.asyncio
    async def test_embedding_generation_success(self, lm_studio_client):
        """Test successful embedding generation."""
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "data": [{"embedding": [0.1] * 384}]
        })
        mock_response.raise_for_status = Mock()
        
        with patch('aiohttp.ClientSession.post', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
            embedding = await lm_studio_client.generate_embedding(
                model="text-embedding-model",
                input_text="Test text"
            )
        
        assert len(embedding) == 384
        assert all(isinstance(x, float) for x in embedding)
    
    @pytest.mark.asyncio
    async def test_embedding_generation_failure(self, lm_studio_client):
        """Test embedding generation failure."""
        with patch('aiohttp.ClientSession.post', side_effect=Exception("Embedding failed")):
            embedding = await lm_studio_client.generate_embedding(
                model="text-embedding-model",
                input_text="Test text"
            )
        
        assert embedding == []
    
    @pytest.mark.asyncio
    async def test_server_health_check(self, lm_studio_client):
        """Test server health check."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"status": "ok"})
        mock_response.raise_for_status = Mock()
        
        with patch('aiohttp.ClientSession.get', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
            is_healthy = await lm_studio_client.check_server_health()
        
        assert is_healthy is True
    
    @pytest.mark.asyncio
    async def test_server_health_check_failure(self, lm_studio_client):
        """Test server health check failure."""
        with patch('aiohttp.ClientSession.get', side_effect=Exception("Server unavailable")):
            is_healthy = await lm_studio_client.check_server_health()
        
        assert is_healthy is False
    
    @pytest.mark.asyncio
    async def test_streaming_chat_completion(self, lm_studio_client):
        """Test streaming chat completion."""
        # Mock streaming response
        async def mock_stream():
            yield b'{"choices": [{"delta": {"content": "Chunk"}}]}'
            yield b'{"choices": [{"delta": {"content": " 1"}}]}'
            yield b'{"choices": [{"delta": {"content": "Chunk 2"}}]}'
        
        mock_response = AsyncMock()
        mock_response.content = AsyncMock()
        mock_response.content.iter_any = mock_stream
        mock_response.raise_for_status = Mock()
        
        with patch('aiohttp.ClientSession.post', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
            chunks = []
            async for chunk in lm_studio_client.stream_chat_completion(
                model="test-model",
                messages=[{"role": "user", "content": "Hello"}]
            ):
                chunks.append(chunk)
        
        assert len(chunks) == 3
        assert "Chunk" in chunks[0]
        assert "1" in chunks[1]
        assert "2" in chunks[2]


class TestLLMServiceIntegration:
    """Test LLM service integration with LM Studio."""
    
    @pytest.fixture
    def llm_service(self):
        """Create an LLM service for testing."""
        return LLMService()
    
    @pytest.mark.asyncio
    async def test_llm_service_initialization(self, llm_service):
        """Test LLM service initialization."""
        assert llm_service.base_url == "http://localhost:1234"
        assert llm_service.api_key == "lm-studio"
        assert llm_service.timeout == 30
    
    @pytest.mark.asyncio
    async def test_generate_completion_with_lm_studio(self, llm_service, mock_environment):
        """Test completion generation with LM Studio."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "choices": [{"message": {"content": "LM Studio response"}}]
            })
            mock_response.raise_for_status = Mock()
            mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await llm_service.generate_completion("Test prompt")
            
            assert result == "LM Studio response"
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_embedding_with_lm_studio(self, llm_service, mock_environment):
        """Test embedding generation with LM Studio."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            mock_response = AsyncMock()
            mock_response.json = AsyncMock(return_value={
                "data": [{"embedding": [0.1] * 384}]
            })
            mock_response.raise_for_status = Mock()
            mock_post.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await llm_service.generate_embedding("Test text")
            
            assert len(result) == 384
            assert all(isinstance(x, float) for x in result)
            mock_post.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_llm_service_availability_check(self, llm_service, mock_environment):
        """Test LLM service availability check."""
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_get.return_value.__aenter__ = AsyncMock(return_value=mock_response)
            mock_get.return_value.__aexit__ = AsyncMock(return_value=None)
            
            result = await llm_service.is_available()
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_llm_service_unavailable(self, llm_service, mock_environment):
        """Test LLM service when unavailable."""
        with patch('aiohttp.ClientSession.get', side_effect=Exception("Service unavailable")):
            result = await llm_service.is_available()
            
            assert result is False
    
    @pytest.mark.asyncio
    async def test_llm_service_timeout_handling(self, llm_service, mock_environment):
        """Test LLM service timeout handling."""
        with patch('aiohttp.ClientSession.post', side_effect=asyncio.TimeoutError()):
            result = await llm_service.generate_completion("Test prompt")
            
            assert result == "Error: Request timed out"
    
    @pytest.mark.asyncio
    async def test_llm_service_retry_mechanism(self, llm_service, mock_environment):
        """Test LLM service retry mechanism."""
        with patch('aiohttp.ClientSession.post') as mock_post:
            # First call fails, second succeeds
            mock_response1 = AsyncMock()
            mock_response1.raise_for_status = Mock(side_effect=Exception("First try failed"))
            
            mock_response2 = AsyncMock()
            mock_response2.json = AsyncMock(return_value={
                "choices": [{"message": {"content": "Retry successful"}}]
            })
            mock_response2.raise_for_status = Mock()
            
            mock_post.side_effect = [
                AsyncMock(__aenter__=AsyncMock(return_value=mock_response1), __aexit__=AsyncMock(return_value=None)),
                AsyncMock(__aenter__=AsyncMock(return_value=mock_response2), __aexit__=AsyncMock(return_value=None))
            ]
            
            result = await llm_service.generate_completion("Test prompt")
            
            assert result == "Retry successful"
            assert mock_post.call_count == 2


class TestLMStudioConfiguration:
    """Test LM Studio configuration and settings."""
    
    def test_default_configuration(self):
        """Test default LM Studio configuration."""
        client = LMStudioClient()
        
        assert client.base_url == "http://localhost:1234"
        assert client.api_key == "lm-studio"
        assert client.timeout == 30
    
    def test_custom_configuration(self):
        """Test custom LM Studio configuration."""
        client = LMStudioClient(
            base_url="http://custom-host:5678",
            api_key="custom-key",
            timeout=60
        )
        
        assert client.base_url == "http://custom-host:5678"
        assert client.api_key == "custom-key"
        assert client.timeout == 60
    
    @pytest.mark.asyncio
    async def test_model_selection(self, lm_studio_client):
        """Test model selection from available models."""
        with patch.object(lm_studio_client, 'get_models', return_value=[
            {"id": "mistralai/mistral-7b-instruct", "object": "model"},
            {"id": "microsoft/phi-3-mini-4k-instruct", "object": "model"},
            {"id": "text-embedding-all-minilm-l6-v2-embedding", "object": "model"}
        ]):
            models = await lm_studio_client.get_models()
            
            # Should be able to select appropriate models
            chat_models = [m for m in models if "embedding" not in m["id"]]
            embedding_models = [m for m in models if "embedding" in m["id"]]
            
            assert len(chat_models) == 2
            assert len(embedding_models) == 1
            assert embedding_models[0]["id"] == "text-embedding-all-minilm-l6-v2-embedding"


class TestLMStudioErrorHandling:
    """Test LM Studio error handling and resilience."""
    
    @pytest.mark.asyncio
    async def test_network_error_handling(self, lm_studio_client):
        """Test handling of network errors."""
        with patch('aiohttp.ClientSession.post', side_effect=aiohttp.ClientError("Network error")):
            response = await lm_studio_client.chat_completion(
                model="test-model",
                messages=[{"role": "user", "content": "Hello"}]
            )
        
        assert "Error" in response
    
    @pytest.mark.asyncio
    async def test_invalid_model_handling(self, lm_studio_client):
        """Test handling of invalid model requests."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock(side_effect=aiohttp.ClientResponseError(
            request_info=Mock(), history=Mock(), status=404, message="Model not found"
        ))
        
        with patch('aiohttp.ClientSession.post', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
            response = await lm_studio_client.chat_completion(
                model="invalid-model",
                messages=[{"role": "user", "content": "Hello"}]
            )
        
        assert "Error" in response
    
    @pytest.mark.asyncio
    async def test_rate_limiting_handling(self, lm_studio_client):
        """Test handling of rate limiting."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock(side_effect=aiohttp.ClientResponseError(
            request_info=Mock(), history=Mock(), status=429, message="Rate limit exceeded"
        ))
        
        with patch('aiohttp.ClientSession.post', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
            response = await lm_studio_client.chat_completion(
                model="test-model",
                messages=[{"role": "user", "content": "Hello"}]
            )
        
        assert "Error" in response
    
    @pytest.mark.asyncio
    async def test_server_maintenance_handling(self, lm_studio_client):
        """Test handling of server maintenance."""
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock(side_effect=aiohttp.ClientResponseError(
            request_info=Mock(), history=Mock(), status=503, message="Service temporarily unavailable"
        ))
        
        with patch('aiohttp.ClientSession.post', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
            response = await lm_studio_client.chat_completion(
                model="test-model",
                messages=[{"role": "user", "content": "Hello"}]
            )
        
        assert "Error" in response


class TestLMStudioPerformance:
    """Test LM Studio performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, lm_studio_client):
        """Test handling of concurrent requests."""
        import time
        
        # Mock successful responses
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "choices": [{"message": {"content": "Response"}}]
        })
        mock_response.raise_for_status = Mock()
        
        with patch('aiohttp.ClientSession.post', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
            start_time = time.time()
            
            # Send multiple concurrent requests
            tasks = [
                lm_studio_client.chat_completion(
                    model="test-model",
                    messages=[{"role": "user", "content": f"Message {i}"}]
                )
                for i in range(5)
            ]
            
            responses = await asyncio.gather(*tasks)
            end_time = time.time()
            
            # Should complete reasonably quickly
            assert end_time - start_time < 10.0  # 10 seconds for 5 concurrent requests
            assert len(responses) == 5
            assert all("Response" in resp for resp in responses)
    
    @pytest.mark.asyncio
    async def test_large_payload_handling(self, lm_studio_client):
        """Test handling of large payloads."""
        large_message = "This is a large message. " * 1000  # Create large content
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "choices": [{"message": {"content": "Processed large message"}}]
        })
        mock_response.raise_for_status = Mock()
        
        with patch('aiohttp.ClientSession.post', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
            response = await lm_studio_client.chat_completion(
                model="test-model",
                messages=[{"role": "user", "content": large_message}]
            )
        
        assert "Processed large message" in response
    
    @pytest.mark.asyncio
    async def test_memory_usage_with_multiple_requests(self, lm_studio_client):
        """Test memory usage with multiple requests."""
        # This would test memory usage patterns
        # For now, we'll test that multiple requests don't cause issues
        
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={
            "choices": [{"message": {"content": "Memory test response"}}]
        })
        mock_response.raise_for_status = Mock()
        
        with patch('aiohttp.ClientSession.post', return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response), __aexit__=AsyncMock(return_value=None))):
            # Send many requests
            for i in range(20):
                response = await lm_studio_client.chat_completion(
                    model="test-model",
                    messages=[{"role": "user", "content": f"Request {i}"}]
                )
                assert "Memory test response" in response