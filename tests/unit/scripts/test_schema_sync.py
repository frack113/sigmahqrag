"""Schema sync test - verifies initdb.sql tables match EXPECTED_TABLES in setup.py."""

import re
from pathlib import Path

from setup import EXPECTED_TABLES


def test_schema_tables_match_sql():
    """Test that CREATE TABLE statements in initdb.sql match EXPECTED_TABLES."""
    sql_path = (
        Path(__file__).parent.parent.parent.parent
        / "src"
        / "infrastructure"
        / "database"
        / "initdb.sql"
    )

    sql_content = sql_path.read_text(encoding="utf-8")

    # Extract table names from CREATE TABLE IF NOT EXISTS statements
    # Pattern matches: CREATE TABLE IF NOT EXISTS table_name (
    create_table_pattern = r"CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\("
    sql_tables = set(re.findall(create_table_pattern, sql_content, re.IGNORECASE))

    # Filter out any non-table matches (like indexes)
    # Only keep tables that are in our expected set or look like real tables
    sql_tables = {t for t in sql_tables if t.lower() not in ("index", "indexes")}

    # Check for drift
    missing_in_sql = EXPECTED_TABLES - sql_tables
    extra_in_sql = sql_tables - EXPECTED_TABLES

    assert not missing_in_sql, (
        f"Tables in EXPECTED_TABLES but missing from initdb.sql: {sorted(missing_in_sql)}"
    )
    assert not extra_in_sql, (
        f"Tables in initdb.sql but not in EXPECTED_TABLES: {sorted(extra_in_sql)}"
    )


def test_schema_version_in_sql():
    """Test that schema_version seed data exists in initdb.sql."""
    sql_path = (
        Path(__file__).parent.parent.parent.parent
        / "src"
        / "infrastructure"
        / "database"
        / "initdb.sql"
    )

    sql_content = sql_path.read_text(encoding="utf-8")

    assert "schema_version" in sql_content, "schema_version seed data missing from initdb.sql"
    assert '("schema_version",' in sql_content or "('schema_version'," in sql_content


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
