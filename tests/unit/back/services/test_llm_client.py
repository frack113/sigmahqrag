"""Tests for LlamaClient."""

from __future__ import annotations


def test_llama_client_init():
    """Test LlamaClient can be instantiated with default URL."""
    from src.back.llamacpp.client import LlamaClient

    client = LlamaClient()
    assert client is not None
    assert client.base_url is not None


def test_llama_client_with_custom_url():
    """Test LlamaClient accepts custom base URL."""
    from src.back.llamacpp.client import LlamaClient

    client = LlamaClient(base_url="http://custom:9999")
    assert client.base_url == "http://custom:9999"


def test_llama_client_has_generate_method():
    """Test LlamaClient has generate method."""
    from src.back.llamacpp.client import LlamaClient

    client = LlamaClient()
    assert hasattr(client, "generate")
    assert callable(client.generate)


def test_llama_client_has_stream_method():
    """Test LlamaClient has generate_stream method."""
    from src.back.llamacpp.client import LlamaClient

    client = LlamaClient()
    assert hasattr(client, "generate_stream")
    assert callable(client.generate_stream)


def test_llama_client_config():
    """Test LlamaClient default config."""
    from src.back.llamacpp.client import LlamaClient

    client = LlamaClient()
    assert client.base_url is not None
    assert "8080" in client.base_url or "127.0.0.1" in client.base_url


def test_llama_client_has_erase_slot_cache():
    """Test LlamaClient has erase_slot_cache method."""
    from src.back.llamacpp.client import LlamaClient

    client = LlamaClient()
    assert hasattr(client, "erase_slot_cache")
    assert callable(client.erase_slot_cache)


def test_llama_client_strips_trailing_slash():
    """Test LlamaClient strips trailing slash from base_url."""
    from src.back.llamacpp.client import LlamaClient

    client = LlamaClient(base_url="http://localhost:8080/")
    assert client.base_url == "http://localhost:8080"
