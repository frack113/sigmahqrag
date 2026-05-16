"""Collection management for Qdrant."""

from __future__ import annotations

import logging
from typing import Any

import qdrant_client

from .client import get_qdrant_client

logger = logging.getLogger(__name__)


async def list_collections(host: str, port: int) -> list[str]:
    """List all collections in Qdrant."""
    try:
        client = get_qdrant_client(host=host, port=port)
        collections_response = client.get_collections()
        return [info.name for info in collections_response.collections]
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
                size=vector_size, distance="Cosine"
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
    """Get information about a collection."""
    try:
        client = get_qdrant_client(host=host, port=port)
        info = client.get_collection(collection_name=collection_name)
        return {
            "name": info.name,
            "vectors_config": str(info.vectors_config),
            "status": "active",
        }
    except Exception as e:
        logger.error(f"Failed to get collection '{collection_name}': {e}")
        raise
