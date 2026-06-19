"""Tests for schema_version type consistency."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from src.config.constants import SCHEMA_VERSION
from src.infrastructure.database import DatabaseService


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


class TestSchemaVersionType:
    def test_get_config_returns_int_for_schema_version(self, db: DatabaseService) -> None:
        db.set_config("schema_version", SCHEMA_VERSION)
        retrieved = db.get_config("schema_version")
        assert isinstance(retrieved, int), f"Expected int, got {type(retrieved)}: {retrieved!r}"
        assert retrieved == SCHEMA_VERSION

    def test_handles_raw_string_input(self, db: DatabaseService) -> None:
        with db._lock:
            db._writer_conn.execute(
                "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                ("schema_version", "1"),
            )
            db._writer_conn.commit()
        retrieved = db.get_config("schema_version")
        assert isinstance(retrieved, int), f"Expected int, got {type(retrieved)}: {retrieved!r}"
        assert retrieved == 1

    def test_handles_json_int_input(self, db: DatabaseService) -> None:
        with db._lock:
            db._writer_conn.execute(
                "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                ("schema_version", json.dumps(1)),
            )
            db._writer_conn.commit()
        retrieved = db.get_config("schema_version")
        assert isinstance(retrieved, int), f"Expected int, got {type(retrieved)}: {retrieved!r}"
        assert retrieved == 1

    def test_other_config_key_not_affected(self, db: DatabaseService) -> None:
        db.set_config("some_string_key", "hello")
        retrieved = db.get_config("some_string_key")
        assert retrieved == "hello"
        assert isinstance(retrieved, str)

    def test_other_config_key_json_parsed_normally(self, db: DatabaseService) -> None:
        db.set_config("some_nested_key", {"nested": True})
        retrieved = db.get_config("some_nested_key")
        assert isinstance(retrieved, dict)
        assert retrieved.get("nested") is True
