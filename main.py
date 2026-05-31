import logging
import re
import sys
from pathlib import Path

from src.back.database import DatabaseService


class _Filter2xx(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelname != "INFO":
            return True
        msg = record.getMessage()
        # Uvicorn access log format: '127.0.0.1 - "GET /path HTTP/1.1" 200 OK'
        return not bool(re.search(r'"\s+2\d{2}\s+\d{3}', msg))


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
    """Initialize in-memory DuckDB schema + seed data and verify tables. Exit on failure."""
    expected = frozenset(
        {
            "config",
            "embedding_config",
            "system_prompts",
            "models",
            "doc_registry",
            "worker_state",
            "git_metadata",
            "git_selected_dirs",
        }
    )
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
        print(f"ERROR: Failed to initialize DuckDB: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    import asyncio
    import copy
    import uvicorn
    from uvicorn.config import LOGGING_CONFIG

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    _ensure_data_folders()
    _ensure_duckdb_tables()

    log_config = copy.deepcopy(LOGGING_CONFIG)
    log_config["filters"] = {
        "filter2xx": {"()": _Filter2xx},
    }
    log_config["handlers"]["access"]["filters"] = ["filter2xx"]

    uvicorn.run(
        "src.main:create_app", host="0.0.0.0", port=7860, factory=True, log_config=log_config
    )
