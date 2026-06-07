"""DuckDB core — singleton, init, persist, generic ops, config table."""

from __future__ import annotations

import json
import logging
import threading
from pathlib import Path
from typing import Any, Self, cast

import duckdb

logger = logging.getLogger(__name__)


def _default_db_path() -> str:
    from src.config.settings import get_config

    return get_config().paths_duckdb_path


_VALID_TABLES = frozenset(
    {
        "config",
        "embedding_config",
        "system_prompts",
        "models",
        "doc_registry",
        "sigma_spec",
        "doc_error",
        "git_metadata",
        "git_selected_dirs",
        "worker_state",
    }
)


class DatabaseServiceCore:
    """DuckDB core — singleton lifecycle, generic table access, config."""

    _instance: DatabaseServiceCore | None = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = Path(db_path or _default_db_path())
        prev = DatabaseServiceCore._instance
        if prev is not None:
            prev.close()
        self._initialized = False
        self._writer_conn = duckdb.connect(":memory:")
        self._conn = self._writer_conn
        # Clear any subclass _instance shadow (from tests/the wild)
        if "_instance" in type(self).__dict__:
            delattr(type(self), "_instance")
        DatabaseServiceCore._instance = self
        logger.info("DatabaseService initialized in-memory (persist path: %s)", self.db_path)

    @classmethod
    def get_instance(cls: type[Self]) -> Self:
        if DatabaseServiceCore._instance is None:
            raise RuntimeError(
                "DatabaseService not initialized. Call main() first or run python main.py"
            )
        return cast(Self, DatabaseServiceCore._instance)

    def initialize(self) -> None:
        if self._initialized:
            logger.warning("initialize() called more than once — skipping")
            return
        initdb_path = Path(__file__).parent / "initdb.sql"
        self._writer_conn.execute(initdb_path.read_text(encoding="utf-8"))
        self._writer_conn.commit()
        if self.db_path.exists():
            self._load_from_file()
        self._initialized = True
        self._conn = self._writer_conn
        logger.info("Schema initialized successfully")

    def _load_from_file(self) -> None:
        with self._lock:
            logger.info("Loading database from %s", self.db_path)
            path = self.db_path.as_posix()
            self._writer_conn.execute(f"ATTACH '{path}' AS file_db (READ_ONLY)")
            for table in _VALID_TABLES:
                try:
                    self._writer_conn.execute(
                        f"INSERT OR REPLACE INTO {table} SELECT * FROM file_db.{table}"
                    )
                except Exception:
                    logger.warning("Table %s not found in existing database — skipping", table)
            self._writer_conn.execute("DETACH file_db")
            logger.info("Loaded tables from disk")

    def persist(self, path: str | None = None) -> None:
        if not self._initialized:
            logger.error("persist() called before initialize()")
            return
        target = Path(path or self.db_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        tmp = target.with_suffix(".duckdb.tmp")
        with self._lock:
            try:
                path_str = tmp.as_posix()
                self._writer_conn.execute(f"ATTACH '{path_str}' AS file_db (TYPE DUCKDB)")
                for table in _VALID_TABLES:
                    self._writer_conn.execute(
                        f"CREATE TABLE file_db.{table} AS SELECT * FROM {table}"
                    )
                self._writer_conn.execute("DETACH file_db")
                if target.exists():
                    target.unlink()
                tmp.rename(target)
                logger.info("Database persisted to %s", target)
            except Exception:
                if tmp.exists():
                    tmp.unlink()
                raise

    def close(self) -> None:
        if getattr(self, "_writer_conn", None) is not None:
            self._writer_conn.close()
            self._writer_conn = None  # type: ignore[assignment]
            self._conn = None  # type: ignore[assignment]
        DatabaseServiceCore._instance = None
        logger.info("DatabaseService closed")

    def _get_reader_connection(self) -> duckdb.DuckDBPyConnection | None:
        return self._writer_conn

    def _safe_query(self, query: str, params: tuple = ()) -> Any:
        with self._lock:
            conn = self._get_reader_connection()
            if conn is None:
                return None
            return conn.execute(query, params).fetchone()

    def get_tables(self) -> list[str]:
        with self._lock:
            return sorted(
                [
                    row[0]
                    for row in self._writer_conn.execute(
                        "SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE'"
                    ).fetchall()
                ]
            )

    def get_table_data(self, table_name: str, limit: int = 50, offset: int = 0) -> list[dict]:
        if table_name not in _VALID_TABLES:
            raise ValueError(f"Invalid table name: {table_name}")
        limit = max(1, min(limit, 1000))
        offset = max(0, offset)
        with self._lock:
            result = self._writer_conn.execute(
                f"SELECT * FROM {table_name} LIMIT ? OFFSET ?",
                [limit, offset],
            )
            col_names = [desc[0] for desc in result.description]
            rows = result.fetchall()
        return [dict(zip(col_names, row)) for row in rows]

    def get_table_count(self, table_name: str) -> int:
        if table_name not in _VALID_TABLES:
            raise ValueError(f"Invalid table name: {table_name}")
        result = self._safe_query(f"SELECT COUNT(*) FROM {table_name}")
        return result[0] if result else 0

    # ------------------------------------------------------------------
    # Config table
    # ------------------------------------------------------------------

    def get_config(self, key: str) -> Any | None:
        result = self._safe_query("SELECT value FROM config WHERE key = ?", (key,))
        if result:
            try:
                return json.loads(result[0])
            except (json.JSONDecodeError, TypeError):
                return result[0]
        return None

    def set_config(
        self, key: str, value: dict[str, Any] | list[Any] | str | int | bool | None
    ) -> None:
        with self._lock:
            self._writer_conn.execute(
                "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (key, json.dumps(value)),
            )
            self._writer_conn.commit()
            try:
                self.persist()
            except Exception:
                logger.warning("Auto-persist after set_config failed (non-fatal)")
