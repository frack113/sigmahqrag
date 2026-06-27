"""Storage operations for Qdrant."""

from __future__ import annotations

import logging
import uuid
from typing import Any

import qdrant_client
from qdrant_client.models import FieldCondition, Filter, MatchValue

from src.infrastructure.vectorstore.client import get_qdrant_client

logger = logging.getLogger(__name__)

DEFAULT_VECTOR_SIZE = 384


def _make_point_id(collection: str, meta: dict[str, Any]) -> str:
    """Generate a deterministic UUID from collection + source_file + chunk_type.

    Falls back to uuid4 when required metadata fields are missing.
    """
    source_file = meta.get("source_file", "")
    chunk_type = meta.get("chunk_type", "")
    if source_file and chunk_type:
        key = f"{collection}:{source_file}:{chunk_type}"
        return str(uuid.uuid5(uuid.NAMESPACE_URL, key))
    return str(uuid.uuid4())


def _delete_by_source(client: Any, collection_name: str, source_file: str) -> None:
    """Delete all points matching metadata.source_file in a collection."""
    try:
        client.delete(
            collection_name=collection_name,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="source_file",
                        match=MatchValue(value=source_file),
                    )
                ]
            ),
        )
    except Exception as e:
        logger.warning("Failed to delete old points for %s: %s", source_file, e)


async def store_embeddings(
    embeddings: list[list[float]],
    documents: list[str],
    metadata: list[dict[str, Any]] | None = None,
    collection_name: str = "sigma_docs",
    vector_size: int = DEFAULT_VECTOR_SIZE,
) -> bool:
    """Store embeddings in Qdrant with delete-before-upsert.

    For each unique source_file, deletes old points before inserting new ones.
    Point IDs are deterministic (uuid5) when source_file + chunk_type are present,
    so the same document always maps to the same point.

    Args:
        embeddings: Embedding vectors
        documents: Original documents
        metadata: Metadata for each document (must contain source_file, chunk_type)
        collection_name: Qdrant collection name
        vector_size: Vector dimension

    Returns:
        True if successful
    """
    if len(documents) != len(embeddings):
        logger.error("Document count must match embedding count")
        return False

    meta_list = metadata if metadata is not None else [{} for _ in documents]

    # Group by source_file for batch delete
    sources_seen: set[str] = set()
    for meta in meta_list:
        src = meta.get("source_file", "")
        if src:
            sources_seen.add(src)

    points = []
    for emb, doc, meta in zip(embeddings, documents, meta_list, strict=True):
        point_id = _make_point_id(collection_name, meta)
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

        # Auto-create collection if missing
        existing_collections = [c.name for c in client.get_collections().collections]
        if collection_name not in existing_collections:
            from qdrant_client.models import Distance, VectorParams

            client.recreate_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

        # Delete old points for each source before upserting
        for src in sources_seen:
            _delete_by_source(client, collection_name, src)

        client.upsert(
            collection_name=collection_name,
            points=points,
        )
        logger.info(
            "Stored %d vectors in %s (cleaned %d sources)",
            len(points),
            collection_name,
            len(sources_seen),
        )
        return True
    except Exception as e:
        logger.error("Failed to store embeddings: %s", e)
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
        from src.infrastructure.vectorstore import QdrantService

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
    client = get_qdrant_client(host=host, port=port)
    try:
        client.delete(
            collection_name=collection_name,
            points_selector=qdrant_client.models.PointIdsList(points=[point_id]),
        )
        logger.info(f"Deleted point {point_id} from {collection_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete point {point_id}: {e}")
        return False
    finally:
        client.close()
