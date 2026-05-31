"""Transforms package.

Exposes the DocumentTransform base contract, the TransformRegistry,
and automatically registers all format-specific transforms on import.
"""

# Import base types first.
from .base import DocumentTransform, TransformConfig, ChunkedDocument
from .registry import TransformRegistry

# Import sigma module to trigger registration.
# This side-effect registers SigmaParser (flat) and SigmaChunker (rich).
from . import sigma  # noqa: F401

__all__ = [
    "DocumentTransform",
    "TransformConfig",
    "ChunkedDocument",
    "TransformRegistry",
]
