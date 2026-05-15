"""Llama.cpp package."""

from src.shared import get_config

from .client import LlamaClient
from .health import check_health
from .service import LlamaBinaryService

LlamaService = LlamaBinaryService


def get_version() -> str | None:
    """Get current llama.cpp version."""
    return get_config().llamacpp_version


def set_version(version: str) -> None:
    """Set llama.cpp version."""
    config = get_config()
    config.llamacpp_version = version
    config.save()


__all__ = [
    "LlamaClient",
    "LlamaBinaryService",
    "LlamaService",
    "check_health",
    "get_version",
    "set_version",
]
