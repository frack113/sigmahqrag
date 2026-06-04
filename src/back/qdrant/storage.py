"""Storage operations for Qdrant."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import qdrant_client

from src.back.qdrant.client import get_qdrant_client

logger = logging.getLogger(__name__)

DEFAULT_VECTOR_SIZE = 384


async def store_embeddings(
    embeddings: list[list[float]],
    documents: list[str],
    metadata: list[dict[str, Any]] | None = None,
    collection_name: str = "sigma_docs",
    vector_size: int = DEFAULT_VECTOR_SIZE,
) -> bool:
    """Store embeddings in Qdrant.

    Args:
        embeddings: Embedding vectors
        documents: Original documents
        metadata: Optional metadata for each document
        collection_name: Qdrant collection name
        vector_size: Vector dimension

    Returns:
        True if successful
    """
    if len(documents) != len(embeddings):
        logger.error("Document count must match embedding count")
        return False

    points = []
    meta_list = metadata if metadata is not None else [{} for _ in documents]

    for emb, doc, meta in zip(embeddings, documents, meta_list, strict=True):
        point_id = str(uuid.uuid4())
        points.append(
            qdrant_client.models.PointStruct(
                id=point_id,
                vector=emb,
                payload={
                    "text": doc,
                    **meta,
                },
            )
        )

    try:
        client = get_qdrant_client()
        existing_collections = [c.name for c in client.get_collections().collections]
        if collection_name not in existing_collections:
            from qdrant_client.models import Distance, VectorParams

            client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
        client.upsert(
            collection_name=collection_name,
            points=points,
        )
        logger.info(f"Stored {len(points)} vectors in {collection_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to store embeddings: {e}")
        return False


async def upsert_by_key(
    embeddings: list[list[float]],
    documents: list[str],
    metadata: list[dict[str, Any]],
    collection_name: str = "sigma_rules",
    vector_size: int = DEFAULT_VECTOR_SIZE,
    key_fields: list[str] | None = None,
) -> bool:
    """Store embeddings in Qdrant using composite key for upsert.

    Uses (rule_id, chunk_type) as upsert key to avoid duplicates.

    Args:
        embeddings: Embedding vectors
        documents: Original documents
        metadata: Metadata dicts containing rule_id and chunk_type
        collection_name: Qdrant collection name
        vector_size: Vector dimension
        key_fields: Override default key fields

    Returns:
        True if successful
    """
    if key_fields is None:
        key_fields = ["rule_id", "chunk_type"]

    if len(documents) != len(embeddings) != len(metadata):
        logger.error("Document, embedding, and metadata counts must match")
        return False

    points = []
    for emb, doc, meta in zip(embeddings, documents, metadata, strict=True):
        # Build composite key from specified fields
        key_parts = []
        for field in key_fields:
            value = meta.get(field)
            if value:
                key_parts.append(str(value))

        if not key_parts:
            logger.warning("Missing key fields, skipping point")
            continue

        raw_key = f"{collection_name}_{'_'.join(key_parts)}"
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, raw_key))
        points.append(
            qdrant_client.models.PointStruct(
                id=point_id,
                vector=emb,
                payload={
                    "text": doc,
                    **meta,
                },
            )
        )

    try:
        client = get_qdrant_client()
        existing_collections = [c.name for c in client.get_collections().collections]
        if collection_name not in existing_collections:
            client.recreate_collection(
                collection_name=collection_name,
                vectors_config=qdrant_client.models.VectorParams(
                    size=vector_size,
                    distance=qdrant_client.models.Distance.COSINE,
                ),
            )
        client.upsert(
            collection_name=collection_name,
            points=points,
        )
        logger.info(f"Upserted {len(points)} vectors with composite keys in {collection_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to upsert embeddings: {e}")
        return False


async def search(
    query_embedding: list[float],
    collection_name: str = "sigma_docs",
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """Search for similar vectors in Qdrant.

    Args:
        query_embedding: Query vector
        collection_name: Qdrant collection name
        top_k: Number of results to return

    Returns:
        List of search results with text, metadata, and score
    """
    try:
        from src.back.qdrant import QdrantService

        service = QdrantService(collection_name=collection_name)
        await service.initialize()

        return await service.search(
            query_embedding=query_embedding,
            top_k=top_k,
        )
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []


async def delete_point(
    collection_name: str,
    point_id: str,
    host: str = "127.0.0.1",
    port: int = 6333,
) -> bool:
    """Delete a point from the collection."""
    try:
        client = get_qdrant_client(host=host, port=port)
        client.delete(
            collection_name=collection_name,
            points_selector=qdrant_client.models.PointIdsList(points=[point_id]),
        )
        logger.info(f"Deleted point {point_id} from {collection_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete point {point_id}: {e}")
        return False
