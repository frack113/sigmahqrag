"""Transforms package.

Exposes the DocumentTransform base contract, the TransformRegistry,
and automatically registers all format-specific transforms on import.
"""

# Import base types first.
from .base import DocumentTransform, TransformConfig
from .registry import TransformRegistry

# Import sigma and markdown modules to trigger registration.
from . import sigma  # noqa: F401
from . import markdown  # noqa: F401

__all__ = [
    "DocumentTransform",
    "TransformConfig",
    "TransformRegistry",
]
