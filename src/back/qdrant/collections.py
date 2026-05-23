"""Collection management for Qdrant."""

from __future__ import annotations

import logging
import re
from typing import Any

import qdrant_client

from .client import get_qdrant_client

logger = logging.getLogger(__name__)


async def list_collections(host: str, port: int) -> list[dict[str, Any]]:
    """List all collections with detailed info."""
    try:
        client = get_qdrant_client(host=host, port=port)
        collections_response = client.get_collections()

        detailed_collections = []
        for info in collections_response.collections:
            name = getattr(info, "name", None)
            if not name:
                # Fallback if .name is not available
                continue
            details = await get_collection(host, port, name)
            details["name"] = name
            detailed_collections.append(details)
        return detailed_collections
    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        raise


async def create_collection(
    host: str, port: int, collection_name: str, vector_size: int = 384
) -> bool:
    """Create a new collection."""
    try:
        client = get_qdrant_client(host=host, port=port)
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qdrant_client.models.VectorParams(
                size=vector_size,
                distance=qdrant_client.models.Distance.COSINE,
            ),
        )
        logger.info(f"Collection '{collection_name}' created successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to create collection '{collection_name}': {e}")
        raise


async def delete_collection(host: str, port: int, collection_name: str) -> bool:
    """Delete an existing collection."""
    try:
        client = get_qdrant_client(host=host, port=port)
        client.delete_collection(collection_name=collection_name)
        logger.info(f"Collection '{collection_name}' deleted successfully.")
        return True
    except Exception as e:
        logger.error(f"Failed to delete collection '{collection_name}': {e}")
        raise


async def get_collection(host: str, port: int, collection_name: str) -> dict[str, Any]:
    """Get information about a collection with defensive extraction."""
    try:
        client = get_qdrant_client(host=host, port=port)
        info = client.get_collection(collection_name=collection_name)

        points_count = 0
        try:
            points_count = client.count(collection_name=collection_name).count
        except Exception:
            pass

        # Defensive extraction of shards and vector size using regex on string representation
        # This avoids AttributeError when SDK structure changes (e.g., info.config vs info.params)
        info_str = str(info)

        shards = 1
        shard_match = re.search(r"shard_number=(\d+)", info_str)
        if shard_match:
            shards = int(shard_match.group(1))
        elif "shard_number" in info_str:  # Fallback for different formats
            match = re.search(r"(\d+)", info_str.split("shard_number")[-1].split(",")[0])
            if match:
                shards = int(match.group(1))

        vector_size = 384
        # Look for size=XXX or similar pattern in the config string
        size_match = re.search(r"size=(\d+)", info_str)
        if size_match:
            vector_size = int(size_match.group(1))
        else:
            # Fallback: search for any digit sequence near 'vectors_config' or 'size'
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
        logger.error(f"Failed to get collection '{collection_name}': {e}")
        raise
