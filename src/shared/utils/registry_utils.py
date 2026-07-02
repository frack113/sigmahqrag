"""Shared registry entry builder for Sigma reference document tracking.

Consolidates the entry-building logic duplicated across:
- sigma_ref_downloader.py (``_make_entry``)
- sigma_ref_processor.py (``_build_head_entry``, ``_build_download_entry``)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.shared.utils import iso_now
from src.shared.utils.crypto_utils import compute_sha256_bytes


def build_registry_entry(
    normalized_url: str,
    content_type: str,
    rule_id: str,
    title: str,
    content_sha256: str = "",
    file_name: str = "",
    file_size: int | None = None,
    embed_status: str = "discovery",
    url_hash: str = "",
    original_url: str = "",
) -> dict[str, Any]:
    """Build a doc_registry entry for a Sigma reference document.

    Parameters
    ----------
    normalized_url :
        Normalized URL of the reference document.
    content_type :
        MIME content type (e.g. ``"markdown"``, ``"html"``).
    rule_id :
        ID of the Sigma rule that references this document.
    title :
        Title of the referencing Sigma rule.
    content_sha256 :
        SHA-256 hex digest of the downloaded content.  Empty string if not
        yet downloaded.
    file_name :
        Local filename.  Defaults to the last path component of the URL.
    file_size :
        File size in bytes.
    embed_status :
        Embedding status (``"discovery"``, ``"head_verified"``, ``"embedded"``).
    url_hash :
        Pre-computed hash of ``normalized_url``.  Computed automatically if
        empty.
    original_url :
        Original (non-normalized) URL.  Falls back to ``normalized_url``.

    Returns
    -------
    dict
        A dictionary compatible with ``_save_registry`` and
        ``batch_upsert_doc_registry``.
    """
    now = iso_now()
    hash_value = url_hash or compute_sha256_bytes(normalized_url.encode())
    name = file_name or Path(normalized_url).name

    return {
        "url_hash": hash_value,
        "org": "sigmaref",
        "repo": "references",
        "content_type": content_type,
        "file_name": name,
        "content_sha256": content_sha256,
        "file_size": file_size or 0,
        "original_url": original_url or normalized_url,
        "normalized_url": normalized_url,
        "rule_id": rule_id,
        "title": title,
        "timestamp": now,
        "last_seen": now,
        "embed_status": embed_status,
    }
