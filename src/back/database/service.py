"""DuckDB storage service — in-memory with explicit persist to disk."""

from src.back.database.core import (
    DatabaseServiceCore,
    _VALID_TABLES,
    _default_db_path,
)
from src.back.database.doc_ops import DatabaseServiceDocOps
from src.back.database.table_ops import DatabaseServiceTableOps


class DatabaseService(
    DatabaseServiceCore,
    DatabaseServiceDocOps,
    DatabaseServiceTableOps,
):
    """Thread-safe DuckDB database service (in-memory) with singleton pattern.

    All operations happen in-memory for zero I/O latency. Call :meth:`persist`
    to flush the current state to disk.
    """


__all__ = ["DatabaseService", "_VALID_TABLES", "_default_db_path"]
