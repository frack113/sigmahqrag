"""Tests for LLM client."""

from __future__ import annotations

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.llm_client import LLMClient


@pytest.fixture
def llm_client() -> LLMClient:
    """Create LLM client with test settings."""
    mock_config = {
        "services": {
            "llama": {
                "base_url": "http://localhost:11434",
                "model_name": "llama3.2",
            }
        }
    }
    with patch("src.services.llm_client.load_config", return_value=mock_config):
        yield LLMClient()


@pytest.mark.asyncio
async def test_generate_success(llm_client: LLMClient) -> None:
    """Test successful LLM generation."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={"response": "Test response"})

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient") as mock_class:
        mock_class.return_value = mock_client
        result = await llm_client.generate(prompt="Test prompt")
        assert result == "Test response"


@pytest.mark.asyncio
async def test_generate_with_context(llm_client: LLMClient) -> None:
    """Test generation with context."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json = AsyncMock(return_value={"response": "Response with context"})

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient") as mock_class:
        mock_class.return_value = mock_client
        result = await llm_client.generate(
            prompt="Question?",
            context="Some context here",
        )
        assert result == "Response with context"


@pytest.mark.asyncio
async def test_generate_connection_error(llm_client: LLMClient) -> None:
    """Test handling of connection error."""
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Cannot connect"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient") as mock_class:
        mock_class.return_value = mock_client
        with pytest.raises(httpx.ConnectError):
            await llm_client.generate(prompt="Test")


@pytest.mark.asyncio
async def test_generate_stream(llm_client: LLMClient) -> None:
    """Test streaming response."""
    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = AsyncMock(return_value=["data: chunk1", "data: chunk2"])
    
    # Create async context manager for stream
    stream_cm = AsyncMock()
    stream_cm.__aenter__ = AsyncMock(return_value=mock_response)
    stream_cm.__aexit__ = AsyncMock(return_value=False)
    
    mock_client = AsyncMock()
    mock_client.stream = MagicMock(return_value=stream_cm)
    
    # AsyncClient as context manager
    client_cm = AsyncMock()
    client_cm.__aenter__ = AsyncMock(return_value=mock_client)
    client_cm.__aexit__ = AsyncMock(return_value=False)

    with patch("httpx.AsyncClient") as mock_class:
        mock_class.return_value = client_cm
        chunks = []
        async for chunk in llm_client.generate_stream(prompt="Test"):
            chunks.append(chunk)
        assert len(chunks) == 2
