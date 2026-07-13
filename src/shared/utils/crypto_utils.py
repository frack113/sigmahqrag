"""Shared cryptographic utility functions."""

from __future__ import annotations

import hashlib
from pathlib import Path


def compute_sha256_str(data: str) -> str:
    """Compute SHA256 hex digest of a string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_sha256_file(path: Path) -> str:
    """Compute SHA256 hex digest of a file's contents."""
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def compute_sha256_bytes(data: bytes) -> str:
    """Compute SHA256 hex digest of bytes."""
    return hashlib.sha256(data).hexdigest()
