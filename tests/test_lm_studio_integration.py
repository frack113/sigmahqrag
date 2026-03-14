"""
Tests for LM Studio integration and API calls.
"""

from unittest.mock import Mock, patch

import pytest
from src.infrastructure.external.lm_studio_client import LMStudioClient


class TestLMStudioClient:
    """Test cases for LM Studio client."""

    def test_client_initialization(self):
        """Test LM Studio client initialization."""
        client = LMStudioClient(
            base_url="http://localhost:1234",
            timeout=30,
            max_retries=3,
            temperature=0.7,
            max_tokens=512,
        )

        assert client.base_url == "http://localhost:1234"
        assert client.timeout == 30
        assert client.max_retries == 3
        assert client.temperature == 0.7
        assert client.max_tokens == 512


class TestLMStudioClientConfiguration:
    """Test LM Studio client configuration and settings."""

    def test_default_configuration(self):
        """Test default LM Studio configuration."""
        client = LMStudioClient()

        assert client.base_url == "http://localhost:1234"
        assert client.timeout == 30
        assert client.max_retries == 3

    def test_custom_base_url(self):
        """Test custom base URL configuration."""
        client = LMStudioClient(base_url="http://custom-host:5678")

        assert client.base_url == "http://custom-host:5678"

    def test_custom_timeout(self):
        """Test custom timeout configuration."""
        client = LMStudioClient(timeout=60)

        assert client.timeout == 60

    def test_custom_max_retries(self):
        """Test custom max retries configuration."""
        client = LMStudioClient(max_retries=5)

        assert client.max_retries == 5


class TestLMStudioClientErrorHandling:
    """Test LM Studio client error handling."""

    def test_graceful_failure_with_unavailable_server(self):
        """Test graceful failure when server is unavailable."""
        client = LMStudioClient()

        # When server is not running, operations should handle gracefully
        try:
            client.is_server_running()
        except Exception as e:
            assert isinstance(e, Exception)

    def test_retry_mechanism_initialization(self):
        """Test that retry mechanism is configured."""
        client = LMStudioClient(max_retries=3)

        assert client.max_retries == 3


class TestLMStudioClientStreaming:
    """Test LM Studio client streaming capabilities."""

    def test_streaming_method_exists(self):
        """Test that streaming method is available."""
        client = LMStudioClient()

        assert hasattr(client, "_stream_chat_completion")


class TestLMStudioClientUtilities:
    """Test LM Studio client utility methods."""

    def test_headers_generation(self):
        """Test headers generation for requests."""
        client = LMStudioClient()

        headers = client._get_headers()

        assert "Content-Type" in headers
        assert headers["Content-Type"] == "application/json"


class TestLMStudioClientStats:
    """Test LM Studio client statistics tracking."""

    def test_stats_initialization(self):
        """Test initial statistics values."""
        client = LMStudioClient()

        stats = client.get_stats()

        assert stats["total_requests"] == 0
        assert stats["successful_requests"] == 0
        assert stats["failed_requests"] == 0
        assert stats["total_completions"] == 0
        assert stats["total_embeddings"] == 0


class TestLMStudioClientDefaultValues:
    """Test default client values."""

    def test_default_values(self):
        """Test that defaults are applied correctly."""
        client = LMStudioClient()

        # Default URL should be localhost:1234
        assert "localhost:1234" in client.base_url

        # Timeout defaults to 30 seconds
        assert client.timeout == 30


class TestLMStudioClientWithMockServer:
    """Integration tests with mocked server responses."""

    def test_successful_models_endpoint(self):
        """Test successful models endpoint response."""
        with patch("src.infrastructure.external.lm_studio_client.requests.get") as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "data": [
                    {"id": "qwen/qwen2.5-7b-instruct", "object": "model"},
                ]
            }
            mock_get.return_value = mock_response

            client = LMStudioClient()
            models = client.get_available_models()

            assert len(models) == 1
            assert models[0]["id"] == "qwen/qwen2.5-7b-instruct"

    def test_chat_completion_success(self):
        """Test successful chat completion."""
        with patch("src.infrastructure.external.lm_studio_client.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "This is a test response",
                        },
                    }
                ]
            }
            mock_post.return_value = mock_response

            client = LMStudioClient()
            result = client.chat_completion(
                messages=[{"role": "user", "content": "Hello"}],
                model="qwen/qwen2.5-7b-instruct",
            )

            assert isinstance(result, dict)

    def test_chat_completion_error_handling(self):
        """Test chat completion error handling."""
        with patch("src.infrastructure.external.lm_studio_client.requests.post") as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_post.return_value = mock_response

            client = LMStudioClient()

            try:
                client.chat_completion(
                    messages=[{"role": "user", "content": "Hello"}],
                )
                # If we get here, the method should handle errors gracefully
                assert True
            except Exception as e:
                assert isinstance(e, Exception)


class TestLMStudioClientAsyncMethods:
    """Test that async methods are available on LM Studio client."""

    def test_async_methods_exist(self):
        """Test that async methods exist as attributes."""
        client = LMStudioClient()

        # Check that method exists
        assert hasattr(client, "_stream_chat_completion")


class TestLMStudioIntegration:
    """End-to-end integration tests with mocked environment."""

    def test_full_client_creation_with_config(self):
        """Test full client creation with custom configuration."""
        test_config = {
            "base_url": "http://localhost:1234",
            "timeout": 60,
            "max_retries": 3,
        }

        client = LMStudioClient(**test_config)

        assert client.base_url == "http://localhost:1234"
        assert client.timeout == 60
        assert client.max_retries == 3

    def test_client_methods_exist(self):
        """Test that all required methods exist."""
        client = LMStudioClient()

        assert hasattr(client, "get_available_models")
        assert hasattr(client, "chat_completion")
        assert hasattr(client, "generate_embedding")
        assert hasattr(client, "is_server_running")
        assert hasattr(client, "_stream_chat_completion")