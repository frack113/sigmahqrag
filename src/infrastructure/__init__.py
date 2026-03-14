"""
Infrastructure layer for SigmaHQ RAG application.

This module provides data access and external integration services.
"""

# Export database services
from .database.sqlite_manager import SQLiteManager, create_sqlite_manager

__all__ = [
    # Database
    "SQLiteManager",
    "create_sqlite_manager",
]