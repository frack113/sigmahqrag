"""Tests for ResponseCache."""

from __future__ import annotations

import time

from src.back.backend.services.cache import ResponseCache


def test_cache_set_and_get() -> None:
    """Test basic set/get operations."""
    cache = ResponseCache(ttl=10)
    cache.set("key1", "response1")
    assert cache.get("key1") == "response1"


def test_cache_miss() -> None:
    """Test cache miss returns None."""
    cache = ResponseCache()
    assert cache.get("nonexistent") is None


def test_cache_expiry() -> None:
    """Test TTL expiration."""
    cache = ResponseCache(ttl=1)
    cache.set("key1", "response1")
    time.sleep(1.1)
    assert cache.get("key1") is None


def test_cache_invalidate() -> None:
    """Test clearing all cache entries."""
    cache = ResponseCache()
    cache.set("key1", "response1")
    cache.set("key2", "response2")
    cache.invalidate()
    assert cache.get("key1") is None
    assert cache.get("key2") is None


def test_cache_eviction() -> None:
    """Test FIFO eviction when max size reached."""
    cache = ResponseCache(max_size=2)
    cache.set("key1", "response1")
    cache.set("key2", "response2")
    cache.set("key3", "response3")  # Should evict key1
    assert cache.get("key1") is None
    assert cache.get("key2") == "response2"
    assert cache.get("key3") == "response3"


def test_cache_remove_existing() -> None:
    """Test removing an existing cache entry."""
    cache = ResponseCache()
    cache.set("key1", "value1")
    cache.remove("key1")
    assert cache.get("key1") is None


def test_cache_remove_nonexistent() -> None:
    """Test removing a nonexistent cache entry (no error)."""
    cache = ResponseCache()
    cache.remove("nonexistent")


def test_generate_key() -> None:
    """Test cache key generation."""
    key1 = ResponseCache.generate_key(query="test", context="context")
    key2 = ResponseCache.generate_key(query="test", context="context")
    key3 = ResponseCache.generate_key(query="different", context="context")

    assert key1 == key2  # Same input = same key
    assert key1 != key3  # Different input = different key
    assert len(key1) == 16  # Truncated hash
