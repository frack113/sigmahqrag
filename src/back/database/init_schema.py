"""Initialize DuckDB schema."""


def _ensure_duckdb_schema() -> None:
    """Initialize DuckDB schema from schema.sql."""
    import duckdb

    conn = duckdb.connect("data/duckdb/sigmahqrag.db")
    with open("src/back/database/schema.sql") as f:
        sql = f.read()
    conn.execute(sql)
    conn.close()


def _ensure_embed_progress_table() -> None:
    """Create embed_progress table with correct schema if missing."""
    import duckdb

    conn = duckdb.connect("data/duckdb/sigmahqrag.db")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS embed_progress ("  # noqa: E501
        "task_id TEXT PRIMARY KEY, "  # noqa: E501
        "task_type TEXT DEFAULT 'embeddings', "  # noqa: E501
        "source_type TEXT DEFAULT '', "  # noqa: E501
        "status TEXT NOT NULL DEFAULT 'none', "  # noqa: E501
        "total INTEGER DEFAULT 0, "  # noqa: E501
        "processed INTEGER DEFAULT 0, "  # noqa: E501
        "errors TEXT, "  # noqa: E501
        "skipped INTEGER DEFAULT 0, "  # noqa: E501
        "current_file TEXT DEFAULT '', "  # noqa: E501
        "collection_name TEXT DEFAULT '', "  # noqa: E501
        "progress_percent REAL DEFAULT 0.0, "  # noqa: E501
        "updated_at TEXT)"  # noqa: E501
    )
    conn.close()
