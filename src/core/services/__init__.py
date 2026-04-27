"""Core services for model management."""

from huggingface_hub import ModelInfo
from .download import (
    AtomicDownloadService,
    ChecksumMismatchError,
    DiskSpaceError,
    DownloadError,
    HFDownloadService,
    NetworkError,
)
from .embedding import EmbeddingManager
from .manager import ModelManager, ModelNotFoundError
from .registry import (
    LocalRegistry,
    ModelRecord,
    RegistryError,
)
from .vram import VRAMEstimator

__all__ = [
    "HFDownloadService",
    "AtomicDownloadService",
    "DownloadError",
    "ChecksumMismatchError",
    "DiskSpaceError",
    "NetworkError",
    "LocalRegistry",
    "ModelRecord",
    "RegistryError",
    "VRAMEstimator",
    "ModelManager",
    "ModelNotFoundError",
    "EmbeddingManager",
]
