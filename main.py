import sys
from pathlib import Path

from src.back.database import DatabaseService


def _ensure_data_folders() -> None:
    base = Path("data").resolve()
    for d in (
        base,
        base / "bin",
        base / "models",
        base / "models" / "llm",
        base / "models" / "embeddings",
        base / "duckdb",
        base / "logs",
        base / "pids",
        base / "qdrant_storage",
        base / "temp",
    ):
        d.mkdir(parents=True, exist_ok=True)


def _ensure_duckdb_tables() -> None:
    """Initialize DuckDB schema + seed data and verify tables. Exit on failure."""
    expected = frozenset(
        {
            "config",
            "embedding_config",
            "system_prompts",
            "models",
            "doc_sigma_ref",
            "embed_progress",
            "worker_state",
            "doc_registry",
            "git_metadata",
            "git_selected_dirs",
        }
    )
    db_path = Path("data/duckdb/sigmahq.duckdb")
    try:
        db = DatabaseService()
        db.initialize()

        tables = frozenset(db.get_tables())
        missing = expected - tables
        if missing:
            print(f"ERROR: DuckDB tables missing after init: {sorted(missing)}", file=sys.stderr)
            db.close()
            sys.exit(1)

        print(f"DuckDB initialized: {len(tables)} tables verified")
        print(f"  embedding_config: {db.get_table_count('embedding_config')} rows")
        print(f"  system_prompts:   {db.get_table_count('system_prompts')} rows")
        print(f"  config:           {db.get_table_count('config')} rows")
        db.close()
    except SystemExit:
        raise
    except Exception as e:
        err = str(e).lower()
        if db_path.exists() and ("another process" in err or "lock" in err or "utilis" in err):
            print("DuckDB already in use by another process, skipping table check")
            return
        print(f"ERROR: Failed to initialize DuckDB: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import uvicorn

    _ensure_data_folders()
    _ensure_duckdb_tables()

    uvicorn.run("src.main:create_app", host="0.0.0.0", port=7860, factory=True, reload=True)
