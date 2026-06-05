"""Transforms package.

Exposes the DocumentTransform base contract, the TransformRegistry,
and automatically registers all format-specific transforms on import.
"""

# Import base types first.
from .base import DocumentTransform, TransformConfig
from .registry import TransformRegistry

# Import modules to trigger registration (order matters — generique last).
from . import sigma  # noqa: F401 — .yml/.yaml
from . import markdown  # noqa: F401 — .md/.markdown
from . import pdf  # noqa: F401 — .pdf
from . import office  # noqa: F401 — .docx/.pptx
from . import generique  # noqa: F401 — catch-all (must be last!)

__all__ = [
    "DocumentTransform",
    "TransformConfig",
    "TransformRegistry",
]
