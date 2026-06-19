"""Tests for DuckDbManager."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.application.system.duckdb import DuckDbManager


@pytest.fixture()
def tmp_duckdb(tmp_path: Path) -> Path:
    """Create a temporary DuckDB database path."""
    return tmp_path / "data" / "duckdb" / "sigmahq.duckdb"


@pytest.fixture()
def manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> DuckDbManager:
    """Create a DuckDbManager instance pointing to a temporary directory."""
    base = tmp_path / "data" / "duckdb" / "sigmahq.duckdb"
    m = DuckDbManager(str(base))
    monkeypatch.setattr(m, "_db_path", base)
    return m


class TestDuckDbManagerCreation:
    def test_defaults_to_standard_path(self) -> None:
        m = DuckDbManager()
        assert "sigmahq.duckdb" in str(m.db_path)

    def test_accepts_custom_path(self, tmp_path: Path) -> None:
        db = tmp_path / "custom.duckdb"
        m = DuckDbManager(str(db))
        assert m.db_path == db

    def test_default_class_method(self) -> None:
        m = DuckDbManager.default()
        assert isinstance(m, DuckDbManager)


class TestDuckDbStatus:
    def test_missing_state(self, manager: DuckDbManager) -> None:
        status = manager.status()
        assert status["state"] == "missing"
        assert status["is_healthy"] is False
        assert status["needs_fix"] is True
        assert status["needs_clean"] is False
        assert status["file_size"] == 0
        assert len(status["tables_missing"]) > 0
        assert status["tables_excess"] == []

    def test_healthy_state(self, manager: DuckDbManager, tmp_path: Path) -> None:
        manager.db_path.parent.mkdir(parents=True, exist_ok=True)
        manager.create_missing()
        status = manager.status()
        assert status["state"] == "healthy"
        assert status["is_healthy"] is True
        assert status["needs_fix"] is False
        assert status["needs_clean"] is False
        assert status["tables_missing"] == []
        assert status["tables_excess"] == []

    def test_dirty_tables_state(self, manager: DuckDbManager, tmp_path: Path) -> None:
        """DB exists but has fewer tables than expected (missing tables)."""
        import duckdb

        manager.db_path.parent.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(str(manager.db_path)) as conn:
            conn.execute("CREATE TABLE config (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        status = manager.status()
        assert status["state"] == "dirty_tables"
        assert status["needs_fix"] is True
        assert status["needs_clean"] is False
        assert len(status["tables_missing"]) == 10
        assert status["tables_excess"] == []

    def test_excess_tables_state(self, manager: DuckDbManager, tmp_path: Path) -> None:
        """DB exists with correct tables plus extra ones."""
        import duckdb

        manager.db_path.parent.mkdir(parents=True, exist_ok=True)
        manager.create_missing()
        with duckdb.connect(str(manager.db_path)) as conn:
            conn.execute("CREATE TABLE temp_table (id INTEGER)")
        status = manager.status()
        assert status["state"] == "excess_tables"
        assert status["needs_fix"] is False
        assert status["needs_clean"] is True
        assert status["tables_missing"] == []
        assert "temp_table" in status["tables_excess"]


class TestDuckDbCreate:
    def test_creates_missing_db(self, manager: DuckDbManager, tmp_path: Path) -> None:
        result = manager.create_missing()
        assert result is not None
        assert manager.db_path.exists()

    def test_idempotent_creation(self, manager: DuckDbManager) -> None:
        manager.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Don't touch the file — let DuckDB create it
        result = manager.create_missing()
        assert result is not None
        assert manager.db_path.exists()

    def test_creates_parent_directory(self, manager: DuckDbManager) -> None:
        manager.create_missing()
        assert manager.db_path.parent.exists()


class TestDuckDbClean:
    def test_removes_excess_tables(self, manager: DuckDbManager, tmp_path: Path) -> None:
        import duckdb

        manager.db_path.parent.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(str(manager.db_path)) as conn:
            conn.execute("CREATE TABLE junk_table (id INTEGER)")
            conn.execute('CREATE TABLE "another_junk" (id INTEGER)')

        result = manager.clean()
        assert result["status"] == "ok"
        assert "junk_table" in result["message"]
        assert "another_junk" in result["message"]

        with duckdb.connect(str(manager.db_path)) as conn:
            existing = sorted(
                [r[0] for r in conn.execute("SELECT table_name FROM duckdb_tables()").fetchall()]
            )
            assert "junk_table" not in existing
            assert "another_junk" not in existing

    def test_noop_when_no_excess(self, manager: DuckDbManager, tmp_path: Path) -> None:
        manager.db_path.parent.mkdir(parents=True, exist_ok=True)
        manager.create_missing()
        result = manager.clean()
        assert "No excess tables" in result["message"]

    def test_noop_when_missing(self, manager: DuckDbManager) -> None:
        result = manager.clean()
        assert "does not exist" in result["message"]


class TestDuckDbHardReset:
    def test_deletes_and_recreates(self, manager: DuckDbManager, tmp_path: Path) -> None:
        manager.db_path.parent.mkdir(parents=True, exist_ok=True)
        manager.db_path.touch()
        result = manager.hard_reset()
        assert manager.db_path.exists()
        assert result["status"] == "ok"

    def test_hard_reset_cleans_excess_tables(self, manager: DuckDbManager, tmp_path: Path) -> None:
        manager.db_path.parent.mkdir(parents=True, exist_ok=True)
        manager.create_missing()
        import duckdb

        with duckdb.connect(str(manager.db_path)) as conn:
            conn.execute("CREATE TABLE junk_table (id INTEGER)")

        result = manager.hard_reset()
        assert result["status"] == "ok"

        with duckdb.connect(str(manager.db_path)) as conn:
            existing = sorted(
                [r[0] for r in conn.execute("SELECT table_name FROM duckdb_tables()").fetchall()]
            )
            assert "junk_table" not in existing
            assert "config" in existing


class TestDuckDbSummary:
    def test_missing_summary(self, manager: DuckDbManager) -> None:
        s = manager.summary()
        assert s["missing"] == 1
        assert s["healthy"] == 0
        assert s["dirty"] == 0
        assert s["excess"] == 0

    def test_healthy_summary(self, manager: DuckDbManager, tmp_path: Path) -> None:
        manager.db_path.parent.mkdir(parents=True, exist_ok=True)
        manager.create_missing()
        s = manager.summary()
        assert s["healthy"] == 1
        assert s["missing"] == 0
        assert s["dirty"] == 0
        assert s["excess"] == 0

    def test_dirty_summary(self, manager: DuckDbManager, tmp_path: Path) -> None:
        import duckdb

        manager.db_path.parent.mkdir(parents=True, exist_ok=True)
        with duckdb.connect(str(manager.db_path)) as conn:
            conn.execute("CREATE TABLE config (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        s = manager.summary()
        assert s["dirty"] == 1
        assert s["healthy"] == 0

    def test_excess_summary(self, manager: DuckDbManager, tmp_path: Path) -> None:
        import duckdb

        manager.db_path.parent.mkdir(parents=True, exist_ok=True)
        manager.create_missing()
        with duckdb.connect(str(manager.db_path)) as conn:
            conn.execute("CREATE TABLE junk_table (id INTEGER)")
        s = manager.summary()
        assert s["excess"] == 1
        assert s["healthy"] == 0
