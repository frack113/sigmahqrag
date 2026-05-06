"""Llama.cpp package."""

from src.config import get_llamacpp_version, set_llamacpp_version

from .client import LlamaClient
from .health import check_health
from .service import LlamaService


def get_version() -> str | None:
    """Get current llama.cpp version."""
    return get_llamacpp_version()


def set_version(version: str) -> None:
    """Set llama.cpp version."""
    set_llamacpp_version(version)


__all__ = ["LlamaClient", "LlamaService", "check_health", "get_version", "set_version"]
