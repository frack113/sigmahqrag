"""Registry management for Sigma reference documents.

Handles loading/saving of the registry from the database.
"""

from __future__ import annotations

import logging
from typing import Any

from src.infrastructure.database import DatabaseService
from src.shared.http import RETRY_STATUSES
from src.shared.utils import iso_now

logger = logging.getLogger(__name__)


def load_registry(path: Any, db: DatabaseService) -> dict[str, Any]:
    """Load the registry from doc_registry for sigmaref org.

    Args:
        path: Output path (unused, kept for API compatibility).
        db: Database service instance.

    Returns:
        Registry dict mapping url_hash → entry.
    """
    entries = db.get_entries_by_org("sigmaref", limit=0)
    registry: dict[str, Any] = {}
    for entry in entries:
        url_hash = entry["url_hash"]
        registry[url_hash] = {
            "original_url": entry.get("original_url", ""),
            "normalized_url": entry.get("normalized_url"),
            "content_type": entry.get("content_type"),
            "rule_id": entry.get("rule_id"),
            "title": entry.get("title"),
            "timestamp": entry.get("timestamp"),
            "content_sha256": entry.get("content_sha256"),
            "embed_status": entry.get("embed_status"),
            "last_seen": entry.get("last_seen"),
            "file_name": entry.get("file_name", ""),
        }
    return registry


def save_registry(registry: dict[str, Any], path: Any, db: DatabaseService) -> None:
    """Save the registry to doc_registry atomically in a single batch.

    Args:
        registry: Registry dict to save.
        path: Output path (unused, kept for API compatibility).
        db: Database service instance.
    """
    rows = []
    now = iso_now()
    for url_hash, entry in registry.items():
        if isinstance(entry, dict):
            rows.append(
                {
                    "url_hash": url_hash,
                    "original_url": entry.get("original_url", ""),
                    "normalized_url": entry.get("normalized_url"),
                    "content_type": entry.get("content_type"),
                    "rule_id": entry.get("rule_id"),
                    "title": entry.get("title"),
                    "timestamp": entry.get("timestamp"),
                    "content_sha256": entry.get("content_sha256"),
                    "org": entry.get("org", "sigmaref"),
                    "repo": entry.get("repo", "references"),
                    "file_name": entry.get("file_name", ""),
                    "file_size": entry.get("file_size"),
                    "embed_status": entry.get("embed_status", "discovery"),
                    "last_seen": entry.get("last_seen", now),
                }
            )
    if rows:
        db.batch_upsert_doc_registry(rows)


def load_error_registry(db: DatabaseService) -> set[str]:
    """Load the set of url_hash values that have previously failed (30x/40x).

    Args:
        db: Database service instance.

    Returns:
        Set of url_hash values that have errors.
    """
    try:
        entries = db.get_doc_errors()
        return {e["url_hash"] for e in entries}
    except Exception:
        logger.warning("Failed to load error registry from DuckDB — proceeding without it")
        return set()


def maybe_record_error(
    db: DatabaseService,
    url_hash: str,
    original_url: str,
    normalized_url: str,
    status_code: int | None,
    rule_id: str,
    rule_title: str,
) -> None:
    """Record a 30x/40x download error in doc_error so it is skipped on retry.

    Args:
        db: Database service instance.
        url_hash: Hash of the normalized URL.
        original_url: Original URL from the rule.
        normalized_url: Normalized URL.
        status_code: HTTP status code (None for network errors).
        rule_id: ID of the Sigma rule that referenced this URL.
        rule_title: Title of the Sigma rule.
    """
    if status_code is None:
        return
    if 300 <= status_code < 500 or (status_code >= 500 and status_code not in RETRY_STATUSES):
        try:
            db.upsert_doc_error(
                {
                    "url_hash": url_hash,
                    "original_url": original_url,
                    "normalized_url": normalized_url,
                    "error_code": status_code,
                    "error_message": f"HTTP {status_code}",
                    "org": "sigmaref",
                    "repo": "references",
                    "timestamp": iso_now(),
                }
            )
        except Exception:
            logger.warning("Failed to record error for %s", normalized_url)
