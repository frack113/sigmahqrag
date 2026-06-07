"""Shared utilities package."""

from src.shared.toml_service import TOMLService as TOMLService
from src.shared.toml_service import deep_merge as deep_merge

__all__ = [
    "TOMLService",
    "deep_merge",
]
