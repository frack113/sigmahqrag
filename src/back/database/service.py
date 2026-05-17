"""DuckDB storage service."""

from __future__ import annotations

import json
import logging
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/duckdb/sigmahq.duckdb"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class DatabaseService:
    """Thread-safe DuckDB database service with singleton pattern."""

    _instance: DatabaseService | None = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self._conn = duckdb.connect(str(self.db_path))
        DatabaseService._instance = self
        logger.info("DatabaseService initialized at %s", self.db_path)

    @classmethod
    def get_instance(cls) -> DatabaseService:
        if cls._instance is None:
            raise RuntimeError(
                "DatabaseService not initialized. Call main() first or run python main.py"
            )
        return cls._instance

    def initialize(self) -> None:
        """Execute schema.sql DDL statements."""
        self._conn.execute(open("src/back/database/schema.sql").read())
        self._conn.commit()
        logger.info("Schema initialized successfully")

    def close(self) -> None:
        """Close database connection and clear singleton."""
        if self._conn:
            self._conn.close()
        DatabaseService._instance = None
        logger.info("DatabaseService closed")

    # =========================================================================
    # GENERIC TABLE OPERATIONS
    # =========================================================================

    def _safe_query(self, query: str, params: tuple = ()) -> Any:
        """Execute a query with parameterized input to prevent SQL injection."""
        with self._lock:
            return self._conn.execute(query, params).fetchone()

    def get_tables(self) -> list[str]:
        """Return sorted list of valid table names."""
        return sorted([row[0] for row in self._conn.execute("SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE'").fetchall()])

    def get_table_data(
        self, table_name: str, limit: int = 50, offset: int = 0
    ) -> list[dict]:
        """Fetch paginated data from a table."""
        limit = max(1, min(limit, 1000))
        offset = max(0, offset)
        with self._lock:
            results = self._conn.execute(
                f"SELECT * FROM {table_name} LIMIT ? OFFSET ?",
                [limit, offset],
            ).fetchall()
            col_names = [desc[0] for desc in self._conn.description]
        return [dict(zip(col_names, row)) for row in results]

    def get_table_count(self, table_name: str) -> int:
        """Return row count for a table."""
        result = self._safe_query(
            f"SELECT COUNT(*) FROM {table_name}",
        )
        return result[0] if result else 0

    # =========================================================================
    # CONFIG TABLE
    # =========================================================================

    def get_config(self, key: str) -> Any | None:
        """Get config value by key (JSON-decoded if possible)."""
        result = self._safe_query("SELECT value FROM config WHERE key = ?", (key,))
        if result:
            try:
                return json.loads(result[0])
            except (json.JSONDecodeError, TypeError):
                return result[0]
        return None

    def set_config(self, key: str, value: dict) -> None:
        """Set config value as JSON."""
        with self._lock:
            self._conn.execute(
                "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (key, json.dumps(value)),
            )
            self._conn.commit()

    # =========================================================================
    # MODELS TABLE
    # =========================================================================

    def get_models(self) -> list[dict]:
        """Fetch all models ordered by repo_id."""
        results = self._conn.execute(
            "SELECT repo_id, model_type, local_path, file_size, status, dimension, index_path, files, updated_at FROM models ORDER BY repo_id"
        ).fetchall()
        rows = []
        for row in results:
            entry: dict[str, Any] = {
                "repo_id": row[0],
                "model_type": row[1],
                "local_path": row[2],
                "file_size": row[3],
                "status": row[4],
                "dimension": row[5],
                "index_path": row[6],
                "updated_at": row[8],
            }
            if row[7]:
                try:
                    entry["files"] = json.loads(row[7])
                except (json.JSONDecodeError, TypeError):
                    entry["files"] = {}
            rows.append(entry)
        return rows

    def upsert_model(self, data: dict) -> None:
        """Upsert a model record."""
        files_json = json.dumps(data.get("files", {})) if data.get("files") else None
        with self._lock:
            self._conn.execute(
                """INSERT INTO models (repo_id, model_type, local_path, file_size, status, dimension, index_path, files, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                 ON CONFLICT (repo_id) DO UPDATE SET
                     model_type = EXCLUDED.model_type,
                     local_path = EXCLUDED.local_path,
                     file_size = EXCLUDED.file_size,
                     status = EXCLUDED.status,
                     dimension = EXCLUDED.dimension,
                     index_path = EXCLUDED.index_path,
                     files = EXCLUDED.files,
                     updated_at = EXCLUDED.updated_at""",
                (
                    data.get("repo_id"),
                    data.get("model_type", "llm"),
                    data.get("local_path"),
                    data.get("file_size", 0),
                    data.get("status", "ready"),
                    data.get("dimension"),
                    data.get("index_path"),
                    files_json,
                    data.get("updated_at"),
                ),
            )
            self._conn.commit()

    def delete_model(self, repo_id: str) -> bool:
        """Delete a model by repo_id. Returns True if deleted."""
        with self._lock:
            result = self._conn.execute("DELETE FROM models WHERE repo_id = ?", (repo_id,))
            self._conn.commit()
            return result.rowcount > 0

    # =========================================================================
    # SYSTEM_PROMPTS TABLE
    # =========================================================================

    def get_prompts(self) -> list[dict]:
        """Fetch all active prompts."""
        results = self._conn.execute(
            "SELECT id, name, description, content, is_active FROM system_prompts ORDER BY name"
        ).fetchall()
        return [
            {
                "id": row[0],
                "name": row[1],
                "description": row[2] or "",
                "content": row[3],
                "is_active": bool(row[4]),
            }
            for row in results
        ]

    def upsert_prompt(self, data: dict) -> None:
        """Upsert a prompt record."""
        with self._lock:
            self._conn.execute(
                """INSERT INTO system_prompts (id, name, description, content, is_active)
                 VALUES (?, ?, ?, ?, ?)
                 ON CONFLICT (id) DO UPDATE SET
                     name = EXCLUDED.name,
                     description = EXCLUDED.description,
                     content = EXCLUDED.content,
                     is_active = EXCLUDED.is_active""",
                (
                    data["id"],
                    data.get("name", ""),
                    data.get("description", ""),
                    data.get("content", ""),
                    data.get("is_active", False),
                ),
            )
            self._conn.commit()

    def delete_prompt(self, prompt_id: str) -> None:
        """Delete a prompt by id."""
        with self._lock:
            self._conn.execute("DELETE FROM system_prompts WHERE id = ?", (prompt_id,))
            self._conn.commit()

    # =========================================================================
    # DOC_SIGMA_REF TABLE
    # =========================================================================

    def get_doc_sigma_ref(self) -> list[dict]:
        """Fetch all document references."""
        results = self._conn.execute(
            "SELECT url_hash, original_url, normalized_url, content_type, rule_id, title, timestamp, content_sha256 FROM doc_sigma_ref ORDER BY url_hash"
        ).fetchall()
        return [
            {
                "url_hash": row[0],
                "original_url": row[1],
                "normalized_url": row[2],
                "content_type": row[3],
                "rule_id": row[4],
                "title": row[5],
                "timestamp": row[6],
                "content_sha256": row[7],
            }
            for row in results
        ]

    def upsert_doc_sigma_ref(self, data: dict) -> None:
        """Upsert a document reference."""
        with self._lock:
            self._conn.execute(
                """INSERT INTO doc_sigma_ref (url_hash, original_url, normalized_url, content_type, rule_id, title, timestamp, content_sha256)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                 ON CONFLICT (url_hash) DO UPDATE SET
                     original_url = EXCLUDED.original_url,
                     normalized_url = EXCLUDED.normalized_url,
                     content_type = EXCLUDED.content_type,
                     rule_id = EXCLUDED.rule_id,
                     title = EXCLUDED.title,
                     timestamp = EXCLUDED.timestamp,
                     content_sha256 = EXCLUDED.content_sha256""",
                (
                    data.get("url_hash"),
                    data.get("original_url"),
                    data.get("normalized_url"),
                    data.get("content_type"),
                    data.get("rule_id"),
                    data.get("title"),
                    data.get("timestamp"),
                    data.get("content_sha256"),
                ),
            )
            self._conn.commit()

    def doc_sigma_ref_exists(self, url_hash: str) -> bool:
        """Check if a document reference exists."""
        result = self._safe_query("SELECT 1 FROM doc_sigma_ref WHERE url_hash = ?", (url_hash,))
        return result is not None

    # =========================================================================
    # EMBED_PROGRESS TABLE
    # =========================================================================

    def upsert_embed_progress(
        self,
        task_id: str,
        source_type: str = "",
        status: str = "pending",
        total: int = 0,
        processed: int = 0,
        errors: str = "",
        skipped: int = 0,
        current_file: str = "",
        collection_name: str = "",
        progress_percent: float = 0.0,
    ) -> None:
        """Upsert embedding progress record."""
        with self._lock:
            self._conn.execute(
                """INSERT INTO embed_progress (task_id, source_type, status, total, processed, errors, skipped, current_file, collection_name, progress_percent, updated_at)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                 ON CONFLICT (task_id) DO UPDATE SET
                     source_type = EXCLUDED.source_type,
                     status = EXCLUDED.status,
                     total = EXCLUDED.total,
                     processed = EXCLUDED.processed,
                     errors = EXCLUDED.errors,
                     skipped = EXCLUDED.skipped,
                     current_file = EXCLUDED.current_file,
                     collection_name = EXCLUDED.collection_name,
                     progress_percent = EXCLUDED.progress_percent,
                     updated_at = EXCLUDED.updated_at""",
                (
                    task_id,
                    source_type,
                    status,
                    total,
                    processed,
                    errors,
                    skipped,
                    current_file,
                    collection_name,
                    progress_percent,
                    _iso_now(),
                ),
            )
            self._conn.commit()

    def get_embed_status(self, task_id: str) -> dict | None:
        """Get progress status for a task."""
        result = self._conn.execute(
            "SELECT task_id, status, total, processed, errors, skipped, current_file, collection_name, progress_percent, updated_at FROM embed_progress WHERE task_id = ?",
            (task_id,)
        ).fetchone()
        if not result:
            return None
        return {
            "task_id": result[0],
            "status": result[1],
            "total": result[2],
            "processed": result[3],
            "errors": result[4],
            "skipped": result[5],
            "current_file": result[6],
            "collection_name": result[7],
            "progress_percent": result[8],
            "updated_at": result[9],
        }

    def get_active_embed_tasks(self) -> list[dict]:
        """Get all pending and running tasks."""
        results = self._conn.execute(
            "SELECT task_id, source_type, status, total, processed, errors, skipped, current_file, collection_name, progress_percent, updated_at FROM embed_progress WHERE status IN ('pending', 'running')"
        ).fetchall()
        return [
            {
                "task_id": row[0],
                "source_type": row[1],
                "status": row[2],
                "total": row[3],
                "processed": row[4],
                "errors": row[5],
                "skipped": row[6],
                "current_file": row[7],
                "collection_name": row[8],
                "progress_percent": row[9],
                "updated_at": row[10],
            }
            for row in results
        ]

    def reset_stale_embed_tasks(self) -> None:
        """Mark running tasks older than 1 hour as failed."""
        with self._lock:
            self._conn.execute(
                """UPDATE embed_progress SET status = 'failed', errors = 'Stale task detected', updated_at = ? WHERE status = 'running' AND updated_at < ?""",
                (_iso_now(), _iso_now()),
            )
            self._conn.commit()

    def get_running_embed_tasks(self) -> list[dict]:
        """Get all running tasks."""
        results = self._conn.execute(
            "SELECT task_id, source_type, status, total, processed, errors, skipped, current_file, collection_name, progress_percent, updated_at FROM embed_progress WHERE status = 'running'"
        ).fetchall()
        return [
            {
                "task_id": row[0],
                "source_type": row[1],
                "status": row[2],
                "total": row[3],
                "processed": row[4],
                "errors": row[5],
                "skipped": row[6],
                "current_file": row[7],
                "collection_name": row[8],
                "progress_percent": row[9],
                "updated_at": row[10],
            }
            for row in results
        ]

    # =========================================================================
    # GIT_METADATA TABLE
    # =========================================================================

    def get_git_metadata(self, repo_key: str) -> dict | None:
        """Get metadata for a repository."""
        result = self._safe_query("SELECT metadata FROM git_metadata WHERE repo_key = ?", (repo_key,))
        if result:
            try:
                return json.loads(result[0])
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    def set_git_metadata(self, repo_key: str, metadata: dict) -> None:
        """Set metadata for a repository."""
        with self._lock:
            self._conn.execute(
                "INSERT INTO git_metadata (repo_key, metadata) VALUES (?, ?) ON CONFLICT (repo_key) DO UPDATE SET metadata = EXCLUDED.metadata",
                (repo_key, json.dumps(metadata)),
            )
            self._conn.commit()

    def delete_git_metadata(self, repo_key: str) -> None:
        """Delete metadata for a repository."""
        with self._lock:
            self._conn.execute("DELETE FROM git_metadata WHERE repo_key = ?", (repo_key,))
            self._conn.commit()

    # =========================================================================
    # GIT_SELECTED_DIRS TABLE
    # =========================================================================

    def get_selected_dirs(self, repo_key: str) -> list[str]:
        """Get selected directories for a repository."""
        results = self._conn.execute(
            "SELECT dir_path FROM git_selected_dirs WHERE repo_key = ? ORDER BY dir_path",
            (repo_key,),
        ).fetchall()
        return [row[0] for row in results]

    def set_selected_dirs(self, repo_key: str, dirs: list[str]) -> None:
        """Set selected directories for a repository."""
        with self._lock:
            self._conn.execute("DELETE FROM git_selected_dirs WHERE repo_key = ?", (repo_key,))
            for d in dirs:
                self._conn.execute("INSERT INTO git_selected_dirs (repo_key, dir_path) VALUES (?, ?)", (repo_key, d))
            self._conn.commit()

    def delete_selected_dirs(self, repo_key: str) -> None:
        """Delete selected directories for a repository."""
        with self._lock:
            self._conn.execute("DELETE FROM git_selected_dirs WHERE repo_key = ?", (repo_key,))
            self._conn.commit()

    # =========================================================================
    # EMBEDDING_CONFIG TABLE
    # =========================================================================

    def get_embedding_config(self) -> dict:
        """Get all embedding configurations."""
        results = self._conn.execute(
            "SELECT doc_type, model, chunk_size, overlap FROM embedding_config ORDER BY doc_type"
        ).fetchall()
        config: dict[str, dict[str, Any]] = {}
        for row in results:
            config[row[0]] = {
                "model": row[1],
                "chunk_size": row[2],
                "overlap": row[3],
            }
        return config

    def set_embedding_config(self, doc_type: str, cfg: dict) -> None:
        """Set embedding configuration for a document type."""
        with self._lock:
            self._conn.execute(
                """INSERT INTO embedding_config (doc_type, model, chunk_size, overlap)
                 VALUES (?, ?, ?, ?)
                 ON CONFLICT (doc_type) DO UPDATE SET
                     model = EXCLUDED.model,
                     chunk_size = EXCLUDED.chunk_size,
                     overlap = EXCLUDED.overlap""",
                (
                    doc_type,
                    cfg.get("model", ""),
                    cfg.get("chunk_size", 512),
                    cfg.get("overlap", 50),
                ),
            )
            self._conn.commit()

    def delete_embedding_config(self, doc_type: str) -> None:
        """Delete embedding configuration for a document type."""
        with self._lock:
            self._conn.execute("DELETE FROM embedding_config WHERE doc_type = ?", (doc_type,))
            self._conn.commit()
