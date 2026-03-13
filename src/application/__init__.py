"""
Application layer for SigmaHQ RAG application.

This module provides high-level application services and orchestration.
Unified entry point: `application.py`
Configuration manager location: `src/shared/config_manager.py`
"""

# Configuration manager is now in shared module
from src.shared.config_manager import ConfigManager, create_config_manager

from .application import (
    SigmaHQApplication,
    create_application,
    create_default_application,
)

__all__ = [
    "SigmaHQApplication",
    "create_application",
    "create_default_application",
    "ConfigManager",
    "create_config_manager",
]
