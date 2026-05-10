"""Model management package.

Consolidates all model management logic (local + HuggingFace).
"""

from src.back.models.download import HFDownloadService
from src.back.models.embedding import EmbeddingManager
from src.back.models.exceptions import (
    ChecksumMismatchError,
    DiskSpaceError,
    DownloadError,
    ModelNotFoundError,
    NetworkError,
    RegistryError,
)
from src.back.models.registry import UnifiedRegistry, create_unified_registry
from src.back.models.types import HFRepo

__all__ = [
    "HFRepo",
    "RegistryError",
    "ModelNotFoundError",
    "DownloadError",
    "ChecksumMismatchError",
    "DiskSpaceError",
    "NetworkError",
    "UnifiedRegistry",
    "create_unified_registry",
    "HFDownloadService",
    "EmbeddingManager",
]
