"""Collection management for Qdrant."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

import qdrant_client

from .client import get_qdrant_client

logger = logging.getLogger(__name__)


def _get_collections_sync(client) -> list:
    """Synchronous wrapper for client.get_collections()."""
    return client.get_collections()


def _get_collection_sync(client, collection_name: str):
    """Synchronous wrapper for client.get_collection()."""
    return client.get_collection(collection_name=collection_name)


def _count_sync(client, collection_name: str) -> int:
    """Synchronous wrapper for client.count()."""
    return client.count(collection_name=collection_name).count


def _create_collection_sync(
    client, collection_name: str, vectors_config, sparse_vectors_config=None
):
    """Synchronous wrapper for client.create_collection()."""
    kwargs = {
        "collection_name": collection_name,
        "vectors_config": vectors_config,
    }
    if sparse_vectors_config is not None:
        kwargs["sparse_vectors_config"] = sparse_vectors_config
    client.create_collection(**kwargs)


def _delete_collection_sync(client, collection_name: str):
    """Synchronous wrapper for client.delete_collection()."""
    client.delete_collection(collection_name=collection_name)


async def list_collections(host: str, port: int) -> list[dict[str, Any]]:
    """List all collections with detailed info."""
    try:
        client = get_qdrant_client(host=host, port=port)
        collections_response = await asyncio.to_thread(_get_collections_sync, client)

        detailed_collections = []
        for info in collections_response.collections:
            name = getattr(info, "name", None)
            if not name:
                continue
            details = await get_collection(host, port, name)
            details["name"] = name
            detailed_collections.append(details)
        return detailed_collections
    except Exception as e:
        logger.error("Failed to list collections: %s: %s", type(e).__name__, e, exc_info=True)
        raise


async def create_collection(
    host: str, port: int, collection_name: str, vector_size: int = 384, enable_hybrid: bool = True
) -> bool:
    """Create a new collection (with optional sparse vector support for hybrid search)."""
    try:
        client = get_qdrant_client(host=host, port=port)
        vectors_config = qdrant_client.models.VectorParams(
            size=vector_size,
            distance=qdrant_client.models.Distance.COSINE,
        )
        sparse_vectors_config: dict[str, Any] | None = None
        if enable_hybrid:
            sparse_vectors_config = {
                "text-sparse": qdrant_client.models.SparseVectorParams(
                    index=qdrant_client.models.SparseIndexParams()
                )
            }
        await asyncio.to_thread(
            _create_collection_sync, client, collection_name, vectors_config, sparse_vectors_config
        )
        logger.info(
            "Collection '%s' created successfully (hybrid=%s).", collection_name, enable_hybrid
        )
        return True
    except Exception as e:
        logger.error(
            "Failed to create collection '%s': %s: %s",
            collection_name,
            type(e).__name__,
            e,
            exc_info=True,
        )
        raise


async def delete_collection(host: str, port: int, collection_name: str) -> bool:
    """Delete an existing collection."""
    try:
        client = get_qdrant_client(host=host, port=port)
        await asyncio.to_thread(_delete_collection_sync, client, collection_name)
        logger.info("Collection '%s' deleted successfully.", collection_name)
        return True
    except Exception as e:
        logger.error(
            "Failed to delete collection '%s': %s: %s",
            collection_name,
            type(e).__name__,
            e,
            exc_info=True,
        )
        raise


async def get_collection(host: str, port: int, collection_name: str) -> dict[str, Any]:
    """Get information about a collection with defensive extraction."""
    try:
        client = get_qdrant_client(host=host, port=port)
        info = await asyncio.to_thread(_get_collection_sync, client, collection_name)

        points_count = 0
        try:
            points_count = await asyncio.to_thread(_count_sync, client, collection_name)
        except Exception:
            pass

        info_str = str(info)

        shards = 1
        shard_match = re.search(r"shard_number=(\d+)", info_str)
        if shard_match:
            shards = int(shard_match.group(1))
        elif "shard_number" in info_str:
            match = re.search(r"(\d+)", info_str.split("shard_number")[-1].split(",")[0])
            if match:
                shards = int(match.group(1))

        vector_size = 384
        size_match = re.search(r"size=(\d+)", info_str)
        if size_match:
            vector_size = int(size_match.group(1))
        else:
            size_fallback = re.search(r"(\d+)", info_str.split("vectors_config")[-1].split(",")[0])
            if size_fallback:
                vector_size = int(size_fallback.group(1))

        return {
            "points": points_count,
            "shards": shards,
            "vector_size": vector_size,
            "status": str(info.status),
        }
    except Exception as e:
        logger.error(
            "Failed to get collection '%s': %s: %s",
            collection_name,
            type(e).__name__,
            e,
            exc_info=True,
        )
        raise
