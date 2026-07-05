"""Qdrant indexing for Sigma rules and reference documents."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from llama_index.core.schema import TextNode

from src.config.settings import get_config
from src.core.pipeline.ingestion import IngestionPipelineBuilder
from src.infrastructure.vectorstore.client import get_qdrant_client
from src.core.sigma.models import SigmaRule

logger = logging.getLogger(__name__)

# Module-level lock registry — prevents concurrent writes to same collection
_collection_locks: dict[str, asyncio.Lock] = {}


def _get_collection_lock(collection_name: str) -> asyncio.Lock:
    """Get or create an asyncio lock per collection."""
    if collection_name not in _collection_locks:
        _collection_locks.setdefault(collection_name, asyncio.Lock())
    return _collection_locks[collection_name]


async def index_sigma_rules(
    rules: list[SigmaRule],
    collection_name: str | None = None,
    mode: str = "flat",
    index_after_upload: bool = False,
) -> dict[str, Any]:
    """Index Sigma rules in Qdrant.

    Args:
        rules: List of SigmaRule to index
        collection_name: Optional collection name override
        mode: 'flat' (one chunk per rule) or 'rich' (multiple chunks per rule)
        index_after_upload: If True, index immediately after upload (incremental)

    Returns:
        Dict with indexing results
    """
    if mode not in ("flat", "rich"):
        raise ValueError(f"Invalid mode: {mode}. Must be 'flat' or 'rich'.")

    config = get_config()
    collection = collection_name or config.qdrant_collection_name

    if not index_after_upload:
        service_client = get_qdrant_client(host=config.qdrant_host, port=config.qdrant_port)
        try:
            # Delete + full reindex strategy: clear old vectors before pipeline insert
            service_client.delete_collection(collection)
        except Exception as e:
            logger.warning(
                "Collection %s not found or cannot be deleted (first run?): %s", collection, e
            )
        finally:
            service_client.close()

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

    lock = _get_collection_lock(collection)
    async with lock:
        try:
            builder = IngestionPipelineBuilder(
                collection_name=collection,
            )
            pipeline = builder.build(skip_splitter=True)  # chunks already created by chunker
            nodes_list = await asyncio.to_thread(
                pipeline.run, documents=nodes, num_workers=builder._num_workers
            )
        except Exception as e:
            logger.error(f"Failed to index via pipeline: {e}")
            return {"success": False, "error": str(e), "indexed": 0}

    logger.info(f"Indexed {len(nodes)} chunks ({len(rules)} rules) to {collection}")
    return {
        "success": True,
        "indexed": len(nodes_list),
        "rules": len(rules),
        "collection": collection,
    }


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

    if rule.references:
        parts.append(f"References: {', '.join(rule.references)}")

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
        "references": rule.references,
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
