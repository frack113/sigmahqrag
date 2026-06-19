"""Test that DatabaseService init has no circular dependency on Config.init_app()."""

from __future__ import annotations

from src.infrastructure.database.core import _default_db_path
from src.config.settings import Config


class TestCircularDependency:
    def test_default_db_path_does_not_trigger_init_app(self) -> None:
        path = _default_db_path()
        assert isinstance(path, str)
        assert path == Config().paths_duckdb_path
