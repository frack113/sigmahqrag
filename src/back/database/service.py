from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, ClassVar

import duckdb

from src.back.database.schema import DDL

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/duckdb/sigmahq.duckdb"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
_VALID_TABLES = frozenset(
    {
        "config",
        "embedding_config",
        "system_prompts",
        "models",
        "doc_sigma_ref",
        "embed_progress",
        "git_metadata",
        "git_selected_dirs",
    }
)


class DatabaseService:
    _instance: ClassVar[DatabaseService | None] = None
    _lock: threading.Lock = threading.Lock()

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self._conn = duckdb.connect(str(self.db_path))
        DatabaseService._instance = self

    @classmethod
    def get_instance(cls) -> DatabaseService:
        if cls._instance is None:
            raise RuntimeError(
                "DatabaseService not initialized. Call main() first or run python main.py"
            )
        return cls._instance

    def initialize(self) -> None:
        for statement in DDL:
            self._conn.execute(statement)
        self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()
        DatabaseService._instance = None

    def _row_count(self, table: str) -> int:
        if table not in _VALID_TABLES:
            raise ValueError(f"Invalid table name: {table}")
        result = self._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()
        return result[0] if result else 0

    def get_tables(self) -> list[str]:
        return sorted(_VALID_TABLES)

    def get_table_data(self, table_name: str, limit: int = 50, offset: int = 0) -> list[dict]:
        if table_name not in _VALID_TABLES:
            raise ValueError(f"Invalid table name: {table_name}")
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
        if table_name not in _VALID_TABLES:
            raise ValueError(f"Invalid table name: {table_name}")
        result = self._conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()
        return result[0] if result else 0

    # Config
    def get_config(self, key: str) -> Any | None:
        result = self._conn.execute("SELECT value FROM config WHERE key = ?", [key]).fetchone()
        if result:
            try:
                return json.loads(result[0])
            except (json.JSONDecodeError, TypeError):
                return result[0]
        return None

    def set_config(self, key: str, value: dict) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                [key, json.dumps(value)],
            )
            self._conn.commit()

    # Models
    def get_models(self) -> list[dict]:
        results = self._conn.execute(
            "SELECT repo_id, model_type, local_path, file_size, status, dimension, index_path, files, updated_at FROM models ORDER BY repo_id"
        ).fetchall()
        rows = []
        for row in results:
            entry = {
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
                [
                    data.get("repo_id"),
                    data.get("model_type", "llm"),
                    data.get("local_path"),
                    data.get("file_size", 0),
                    data.get("status", "ready"),
                    data.get("dimension"),
                    data.get("index_path"),
                    files_json,
                    data.get("updated_at"),
                ],
            )
            self._conn.commit()

    def delete_model(self, repo_id: str) -> bool:
        with self._lock:
            result = self._conn.execute("DELETE FROM models WHERE repo_id = ?", [repo_id])
            self._conn.commit()
            return result.rowcount > 0

    # Prompts
    def get_prompts(self) -> list[dict]:
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
        with self._lock:
            self._conn.execute(
                """INSERT INTO system_prompts (id, name, description, content, is_active)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    content = EXCLUDED.content,
                    is_active = EXCLUDED.is_active""",
                [
                    data["id"],
                    data.get("name", ""),
                    data.get("description", ""),
                    data.get("content", ""),
                    data.get("is_active", False),
                ],
            )
            self._conn.commit()

    def delete_prompt(self, prompt_id: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM system_prompts WHERE id = ?", [prompt_id])
            self._conn.commit()

    # Doc sigma ref
    def get_doc_sigma_ref(self) -> list[dict]:
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
                [
                    data.get("url_hash"),
                    data.get("original_url"),
                    data.get("normalized_url"),
                    data.get("content_type"),
                    data.get("rule_id"),
                    data.get("title"),
                    data.get("timestamp"),
                    data.get("content_sha256"),
                ],
            )
            self._conn.commit()

    def doc_sigma_ref_exists(self, url_hash: str) -> bool:
        result = self._conn.execute(
            "SELECT 1 FROM doc_sigma_ref WHERE url_hash = ?", [url_hash]
        ).fetchone()
        return result is not None

    # Embed progress
    def upsert_embed_progress(self, data: dict) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO embed_progress (task_id, status, total, processed, errors, skipped, current_file, collection_name, started_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (task_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    total = EXCLUDED.total,
                    processed = EXCLUDED.processed,
                    errors = EXCLUDED.errors,
                    skipped = EXCLUDED.skipped,
                    current_file = EXCLUDED.current_file,
                    collection_name = EXCLUDED.collection_name,
                    started_at = EXCLUDED.started_at,
                    updated_at = EXCLUDED.updated_at""",
                [
                    data.get("task_id"),
                    data.get("status", "pending"),
                    data.get("total", 0),
                    data.get("processed", 0),
                    data.get("errors", 0),
                    data.get("skipped", 0),
                    data.get("current_file", ""),
                    data.get("collection_name", ""),
                    data.get("started_at"),
                    data.get("updated_at"),
                ],
            )
            self._conn.commit()

    def get_embed_progress(self, task_id: str) -> dict | None:
        result = self._conn.execute(
            "SELECT task_id, status, total, processed, errors, skipped, current_file, collection_name, started_at, updated_at FROM embed_progress WHERE task_id = ?",
            [task_id],
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
            "started_at": result[8],
            "updated_at": result[9],
        }

    def get_running_embed_tasks(self) -> list[dict]:
        results = self._conn.execute(
            "SELECT task_id, status, total, processed, errors, skipped, current_file, collection_name, started_at, updated_at FROM embed_progress WHERE status = 'running'"
        ).fetchall()
        return [
            {
                "task_id": row[0],
                "status": row[1],
                "total": row[2],
                "processed": row[3],
                "errors": row[4],
                "skipped": row[5],
                "current_file": row[6],
                "collection_name": row[7],
                "started_at": row[8],
                "updated_at": row[9],
            }
            for row in results
        ]

    def reset_stale_embed_tasks(self) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE embed_progress SET status = 'failed', updated_at = ? WHERE status = 'running'",
                [_iso_now()],
            )
            self._conn.commit()

    # Git metadata
    def get_git_metadata(self, repo_key: str) -> dict | None:
        result = self._conn.execute(
            "SELECT metadata FROM git_metadata WHERE repo_key = ?", [repo_key]
        ).fetchone()
        if result:
            try:
                return json.loads(result[0])
            except (json.JSONDecodeError, TypeError):
                return None
        return None

    def set_git_metadata(self, repo_key: str, metadata: dict) -> None:
        with self._lock:
            self._conn.execute(
                "INSERT INTO git_metadata (repo_key, metadata) VALUES (?, ?) ON CONFLICT (repo_key) DO UPDATE SET metadata = EXCLUDED.metadata",
                [repo_key, json.dumps(metadata)],
            )
            self._conn.commit()

    def delete_git_metadata(self, repo_key: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM git_metadata WHERE repo_key = ?", [repo_key])
            self._conn.commit()

    # Git selected dirs
    def get_selected_dirs(self, repo_key: str) -> list[str]:
        results = self._conn.execute(
            "SELECT dir_path FROM git_selected_dirs WHERE repo_key = ? ORDER BY dir_path",
            [repo_key],
        ).fetchall()
        return [row[0] for row in results]

    def set_selected_dirs(self, repo_key: str, dirs: list[str]) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM git_selected_dirs WHERE repo_key = ?", [repo_key])
            for d in dirs:
                self._conn.execute(
                    "INSERT INTO git_selected_dirs (repo_key, dir_path) VALUES (?, ?)",
                    [repo_key, d],
                )
            self._conn.commit()

    def delete_selected_dirs(self, repo_key: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM git_selected_dirs WHERE repo_key = ?", [repo_key])
            self._conn.commit()

    # Embedding config
    def get_embedding_config(self) -> dict:
        results = self._conn.execute(
            "SELECT doc_type, model, chunk_size, overlap FROM embedding_config ORDER BY doc_type"
        ).fetchall()
        config = {}
        for row in results:
            config[row[0]] = {
                "model": row[1],
                "chunk_size": row[2],
                "overlap": row[3],
            }
        return config

    def set_embedding_config(self, doc_type: str, cfg: dict) -> None:
        with self._lock:
            self._conn.execute(
                """INSERT INTO embedding_config (doc_type, model, chunk_size, overlap)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (doc_type) DO UPDATE SET
                    model = EXCLUDED.model,
                    chunk_size = EXCLUDED.chunk_size,
                    overlap = EXCLUDED.overlap""",
                [
                    doc_type,
                    cfg.get("model", ""),
                    cfg.get("chunk_size", 512),
                    cfg.get("overlap", 50),
                ],
            )
            self._conn.commit()

    def delete_embedding_config(self, doc_type: str) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM embedding_config WHERE doc_type = ?", [doc_type])
            self._conn.commit()
