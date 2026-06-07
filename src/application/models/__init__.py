"""Model management package.

Consolidates all model management logic (local + HuggingFace).
"""

from src.application.models.download import HFDownloadService
from src.application.models.embedding import EmbeddingManager
from src.application.models.exceptions import (
    ChecksumMismatchError,
    DiskSpaceError,
    DownloadError,
    ModelNotFoundError,
    NetworkError,
    RegistryError,
)
from src.application.models.registry import UnifiedRegistry
from src.application.models.types import HFRepo

__all__ = [
    "HFRepo",
    "RegistryError",
    "ModelNotFoundError",
    "DownloadError",
    "ChecksumMismatchError",
    "DiskSpaceError",
    "NetworkError",
    "UnifiedRegistry",
    "HFDownloadService",
    "EmbeddingManager",
]
