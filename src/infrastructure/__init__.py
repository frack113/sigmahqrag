"""
Infrastructure layer for SigmaHQ RAG application.

This module provides data access and external integration services.
"""

# Export database services
from .database.sqlite_manager import SQLiteManager, create_sqlite_manager

# Export external services
from .external.github_client import GitHubClient, create_github_client
from .external.lm_studio_client import LMStudioClient, create_lm_studio_client

# Export file system services
from .file_system.file_processor import FileProcessor, create_file_processor
from .file_system.file_storage import FileStorage, create_file_storage

__all__ = [
    # Database
    "SQLiteManager",
    "create_sqlite_manager",
    
    # File System
    "FileProcessor",
    "create_file_processor",
    "FileStorage", 
    "create_file_storage",
    
    # External
    "GitHubClient",
    "create_github_client",
    "LMStudioClient",
    "create_lm_studio_client",
]