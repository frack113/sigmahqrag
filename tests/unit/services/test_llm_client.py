"""Tests for LLM client."""

from __future__ import annotations


def test_llm_client_init():
    """Test LLM client can be instantiated."""
    from src.core.services.llm_client import LLMClient

    client = LLMClient()
    assert client is not None
    assert client.base_url is not None


def test_llm_client_has_generate_method():
    """Test LLM client has generate method."""
    from src.core.services.llm_client import LLMClient

    client = LLMClient()
    assert hasattr(client, "generate")
    assert callable(client.generate)


def test_llm_client_has_stream_method():
    """Test LLM client has generate_stream method."""
    from src.core.services.llm_client import LLMClient

    client = LLMClient()
    assert hasattr(client, "generate_stream")
    assert callable(client.generate_stream)


def test_llm_client_config():
    """Test LLM client has correct config."""
    from src.core.services.llm_client import LLMClient

    client = LLMClient()
    assert client.base_url is not None
    assert client.timeout > 0
