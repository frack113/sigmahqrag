"""Model management exceptions."""

from __future__ import annotations


class RegistryError(Exception):
    """Registry operation error."""

    pass


class ModelNotFoundError(Exception):
    """Model not found in registry."""

    pass


class DownloadError(Exception):
    """Download operation error."""

    pass


class ChecksumMismatchError(DownloadError):
    """Checksum verification failed."""

    pass


class DiskSpaceError(DownloadError):
    """Insufficient disk space."""

    pass


class NetworkError(DownloadError):
    """Network operation failed."""

    pass
