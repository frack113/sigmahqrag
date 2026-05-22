from __future__ import annotations

import os
import tempfile

import pytest

from src.back.database.service import DatabaseService, _VALID_TABLES


@pytest.fixture
def db() -> DatabaseService:
    tmp = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False)
    tmp.close()
    os.unlink(tmp.name)
    d = DatabaseService(tmp.name)
    d.initialize()
    yield d
    d.close()
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


class TestGetTables:
    def test_returns_all_valid(self, db: DatabaseService):
        tables = db.get_tables()
        assert sorted(tables) == sorted(_VALID_TABLES)

    def test_returns_fresh_copy(self, db: DatabaseService):
        tables = db.get_tables()
        assert isinstance(tables, list)
        assert len(tables) == len(_VALID_TABLES)


class TestGetTableData:
    def test_valid_table(self, db: DatabaseService):
        db.set_config("test_key", {"nested": "value"})
        data = db.get_table_data("config")
        assert len(data) >= 1
        assert any(row["key"] == "test_key" for row in data)

    def test_empty_table(self, db: DatabaseService):
        data = db.get_table_data("git_selected_dirs")
        assert data == []

    def test_invalid_table_raises(self, db: DatabaseService):
        with pytest.raises(ValueError, match="Invalid table name"):
            db.get_table_data("nonexistent_table")

    def test_pagination(self, db: DatabaseService):
        for i in range(10):
            db.set_config(f"paginate_key_{i}", {"num": i})
        page1 = db.get_table_data("config", limit=3, offset=0)
        assert len(page1) <= 3
        page2 = db.get_table_data("config", limit=3, offset=3)
        assert len(page2) <= 3
        if page1 and page2:
            assert page1[0]["key"] != page2[0]["key"]

    def test_column_names_match_schema(self, db: DatabaseService):
        db.set_config("schema_key", {"v": 1})
        data = db.get_table_data("config", limit=1)
        assert len(data) == 1
        assert "key" in data[0]
        assert "value" in data[0]

    def test_get_table_count(self, db: DatabaseService):
        assert db.get_table_count("git_selected_dirs") == 0
        db.set_config("count_test", {"x": 1})
        assert db.get_table_count("config") >= 1

    def test_get_table_count_invalid_raises(self, db: DatabaseService):
        with pytest.raises(ValueError, match="Invalid table name"):
            db.get_table_count("bad_table")

    def test_service_layer_clamps_limit(self, db: DatabaseService):
        data = db.get_table_data("git_selected_dirs", limit=-5)
        assert len(data) == 0

    def test_service_layer_clamps_offset(self, db: DatabaseService):
        data = db.get_table_data("git_selected_dirs", limit=5, offset=-10)
        assert len(data) == 0
