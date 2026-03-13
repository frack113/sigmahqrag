# This file has been deprecated.
# Data handling is now managed by:
# - src/infrastructure/database_setup.py for SQLite database operations
# - src/core/rag_service.py for document processing and embeddings
# - src/shared/utils.py for general utility functions

from typing import Any


class DataService:
    """
    Deprecated: Data handling is now distributed across multiple modules.
    
    Use the following modules instead:
    - Database operations: src/infrastructure/database_setup.DatabaseSetup
    - RAG document processing: src/core.rag_service.RAGService
    - File operations: src.shared.utils (get_file_info, format_size, etc.)
    """

    def __init__(self):
        """Deprecated - use database setup modules directly."""
        pass


def save_document(file_path: str, metadata: dict | None = None) -> bool:
    """
    Use RAGService for document processing and storage.
    
    from src.core.rag_service import RAGService
    
    rag_service = RAGService()
    await rag_service.add_document(file_path, metadata=metadata)
    """
    raise DeprecationWarning(
        "Use RAGService.from_file() or add_document() instead"
    )


def load_documents() -> list[dict]:
    """
    Use SQLite database queries for document retrieval.
    
    from src.infrastructure.database_setup import DatabaseSetup
    
    db = DatabaseSetup()
    info = db.get_database_info()
    """
    raise DeprecationWarning(
        "Use DatabaseSetup methods like get_database_info() or direct SQLite queries"
    )