"""Download services for HuggingFace models (wrapper for backward compatibility)."""

from src.back.backend.huggingface import (
    HFDownloadService,
    create_download_service,
)


def create_hf_download_service() -> HFDownloadService:
    """Create an HFDownloadService instance."""
    return create_download_service()


class DownloadError(Exception):
    """Download operation error."""

    pass
