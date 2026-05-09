"""Qdrant indexing for Sigma rules."""

from __future__ import annotations

import logging
import os
from typing import Any

from llama_index.core.schema import TextNode

from src.back.backend.qdrant import QdrantService
from src.back.documents.models import SigmaRule

logger = logging.getLogger(__name__)

DEFAULT_COLLECTION = "sigma_rules"
EMBEDDING_DIM = 384


def get_config() -> dict[str, str]:
    """Get configuration from environment variables."""
    return {
        "qdrant_url": os.environ.get("QDRANT_URL", "127.0.0.1:6333"),
        "qdrant_collection": os.environ.get("QDRANT_COLLECTION", DEFAULT_COLLECTION),
        "embed_model": os.environ.get("EMBED_MODEL", "default"),
    }


async def index_sigma_rules(
    rules: list[SigmaRule],
    collection_name: str | None = None,
) -> dict[str, Any]:
    """Index Sigma rules in Qdrant.

    Args:
        rules: List of SigmaRule to index
        collection_name: Optional collection name override

    Returns:
        Dict with indexing results
    """
    config = get_config()
    collection = collection_name or config["qdrant_collection"]

    host, port_str = config["qdrant_url"].split(":")
    port = int(port_str)

    service = QdrantService(
        collection_name=collection,
        vector_size=EMBEDDING_DIM,
        host=host,
        port=port,
    )

    try:
        await service.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant: {e}")
        return {"success": False, "error": str(e), "indexed": 0}

    nodes = []
    for rule in rules:
        try:
            text = _sigma_rule_to_text(rule)
            metadata = _sigma_rule_to_metadata(rule)

            nodes.append(
                TextNode(
                    text=text,
                    metadata=metadata,
                    id_=rule.id,
                )
            )
        except Exception as e:
            logger.warning(f"Failed to create node for {rule.id}: {e}")
            continue

    if not nodes:
        return {"success": True, "indexed": 0}

    try:
        embeddings = await _generate_embeddings(nodes)
        await service.add_vectors(
            embeddings=embeddings,
            documents=[n.text for n in nodes],
            metadata=[n.metadata for n in nodes],
        )
    except Exception as e:
        logger.error(f"Failed to add vectors: {e}")
        return {"success": False, "error": str(e), "indexed": 0}

    logger.info(f"Indexed {len(rules)} rules to {collection}")
    return {"success": True, "indexed": len(rules), "collection": collection}


def _sigma_rule_to_text(rule: SigmaRule) -> str:
    """Convert SigmaRule to text for embedding.

    Args:
        rule: SigmaRule to convert

    Returns:
        Text representation
    """
    parts = [f"Title: {rule.title}"]

    if rule.description:
        parts.append(f"Description: {rule.description}")

    condition = rule.condition
    if isinstance(condition, list):
        condition = " and ".join(str(c) for c in condition)
    parts.append(f"Condition: {condition}")

    if rule.tags:
        parts.append(f"Tags: {', '.join(rule.tags)}")

    if rule.level:
        parts.append(f"Level: {rule.level}")

    return "\n".join(parts)


def _sigma_rule_to_metadata(rule: SigmaRule) -> dict[str, Any]:
    """Convert SigmaRule to metadata dict.

    Args:
        rule: SigmaRule to convert

    Returns:
        Metadata dictionary
    """
    return {
        "rule_id": rule.id,
        "title": rule.title,
        "author": rule.author,
        "date": rule.date,
        "level": rule.level,
        "status": rule.status,
        "tags": rule.tags,
        "logsource": rule.logsource,
    }


async def _generate_embeddings(nodes: list[TextNode]) -> list[list[float]]:
    """Generate embeddings for nodes.

    Args:
        nodes: List of TextNode

    Returns:
        List of embedding vectors
    """
    from src.rag.embeddings import get_embedding_model

    embed_model = get_embedding_model()
    texts = [node.text for node in nodes]

    embeddings: list[list[float]] = []
    for text in texts:
        embedding = await embed_model.aget_text_embedding(text)
        embeddings.append(embedding)

    return embeddings


async def check_duplicate(rule_id: str, collection: str) -> bool:
    """Check if rule already exists in collection.

    Args:
        rule_id: Rule ID to check
        collection: Collection name

    Returns:
        True if duplicate exists
    """
    config = get_config()
    host, port_str = config["qdrant_url"].split(":")
    port = int(port_str)

    service = QdrantService(
        collection_name=collection,
        vector_size=EMBEDDING_DIM,
        host=host,
        port=port,
    )

    try:
        await service.initialize()
    except Exception:
        return False

    try:
        results = await service.search(
            query_embedding=[0.0] * EMBEDDING_DIM,
            top_k=100,
        )
        for r in results:
            if r.get("metadata", {}).get("rule_id") == rule_id:
                return True
    except Exception:
        pass

    return False

