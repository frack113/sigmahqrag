"""DuckDB storage service package."""

from typing import Protocol

from src.infrastructure.database.service import DatabaseService


class DatabaseServiceProtocol(Protocol):
    """Protocol for database service to enable dependency injection in tests."""

    def initialize(self) -> None: ...
    def get_tables(self) -> list[str]: ...
    def get_table_count(self, table_name: str) -> int: ...
    def set_config(self, key: str, value: int) -> None: ...
    def close(self) -> None: ...


__all__ = ["DatabaseService", "DatabaseServiceProtocol"]
