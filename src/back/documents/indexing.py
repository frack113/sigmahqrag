"""Qdrant indexing for Sigma rules."""

from __future__ import annotations

import logging
from typing import Any

from llama_index.core.schema import TextNode

from src.shared.schemas.sigma_rule import SigmaRule
from src.back.qdrant import QdrantService
from src.core.pipeline.ingestion import get_embedding_dimension
from src.config.settings import get_config

logger = logging.getLogger(__name__)


async def index_sigma_rules(
    rules: list[SigmaRule],
    collection_name: str | None = None,
    mode: str = "flat",
) -> dict[str, Any]:
    """Index Sigma rules in Qdrant.

    Args:
        rules: List of SigmaRule to index
        collection_name: Optional collection name override
        mode: 'flat' (one chunk per rule) or 'rich' (multiple chunks per rule)

    Returns:
        Dict with indexing results
    """
    if mode not in ("flat", "rich"):
        raise ValueError(f"Invalid mode: {mode}. Must be 'flat' or 'rich'.")

    config = get_config()
    collection = collection_name or config.qdrant_collection_name
    embed_dim = get_embedding_dimension()

    service = QdrantService(
        collection_name=collection,
        vector_size=embed_dim,
        host=config.qdrant_host,
        port=config.qdrant_port,
    )

    try:
        await service.initialize()
    except Exception as e:
        logger.error(f"Failed to initialize Qdrant: {e}")
        return {"success": False, "error": str(e), "indexed": 0}

    nodes = []
    for rule in rules:
        try:
            if mode == "flat":
                text = _sigma_rule_to_text(rule)
                metadata = _sigma_rule_to_metadata(rule)
                nodes.append(
                    TextNode(
                        text=text,
                        metadata=metadata,
                        id_=rule.id,
                    )
                )
            else:
                # Rich mode: one rule -> multiple chunks
                rich_chunks = _sigma_rule_to_rich_chunks(rule)
                nodes.extend(rich_chunks)
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

    logger.info(f"Indexed {len(nodes)} chunks ({len(rules)} rules) to {collection}")
    return {"success": True, "indexed": len(nodes), "rules": len(rules), "collection": collection}


def _sigma_rule_to_text(rule: SigmaRule) -> str:
    """Convert SigmaRule to flat text for embedding (one chunk per rule)."""
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
    """Convert SigmaRule to metadata dict."""
    return {
        "rule_id": rule.id,
        "title": rule.title,
        "author": rule.author,
        "date": rule.date,
        "level": rule.level,
        "status": rule.status,
        "tags": rule.tags,
        "logsource": rule.logsource,
        "chunk_type": "full_rule",
    }


def _sigma_rule_to_rich_chunks(rule: SigmaRule) -> list[TextNode]:
    """Convert SigmaRule to multiple enriched chunks for rich mode."""
    from src.core.sigma.chunker import chunk_sigma_rules_rich

    # Reconstruct a dict from SigmaRule for the chunker
    rule_dict = {
        "id": rule.id,
        "title": rule.title,
        "description": rule.description,
        "level": rule.level,
        "status": rule.status,
        "tags": rule.tags,
        "logsource": rule.logsource,
        "detection": getattr(rule, "detection", {}),
        "condition": rule.condition if isinstance(rule.condition, str) else "",
        "falsepositives": rule.falsepositives,
        "references": rule.references,
        "author": rule.author,
        "date": rule.date,
        "modified": rule.modified,
    }

    chunks = chunk_sigma_rules_rich(rule_dict)
    nodes: list[TextNode] = []

    for chunk_data in chunks:
        meta = chunk_data.get("metadata", {}).copy()
        meta["rule_id"] = rule.id
        meta["chunk_type"] = chunk_data.get("chunk_type", "default")
        nodes.append(
            TextNode(
                text=chunk_data.get("text", ""),
                metadata=meta,
                id_=f"{rule.id}_{chunk_data.get('chunk_type', 'chunk')}",
            )
        )

    return nodes


async def _generate_embeddings(nodes: list[TextNode]) -> list[list[float]]:
    """Generate embeddings for nodes using batched inference."""
    from src.core.embedding.factory import embed_documents
    from llama_index.core.schema import Document

    docs = [Document(text=node.text) for node in nodes]
    return await embed_documents(docs)
