# This file has been deprecated.
# Repository patterns are now handled by:
# - src/infrastructure/database_setup.DatabaseSetup for database operations
# - Direct SQLite queries where needed
from typing import Any


class RepositoryService:
    """
    Deprecated: Use DatabaseSetup or direct database queries instead.
    
    SQLite is used directly through DatabaseSetup class methods.
    """

    def __init__(self):
        """Deprecated - use DatabaseSetup instead."""
        pass


def get_documents() -> list[dict]:
    """Use DatabaseSetup.get_database_info()."""
    raise DeprecationWarning(
        "Use DatabaseSetup.get_database_info() for SQLite queries"
    )


def save_data(data: dict) -> bool:
    """Use DatabaseSetup to perform database operations."""
    raise DeprecationWarning(
        "Use DatabaseSetup methods for database operations"
    )