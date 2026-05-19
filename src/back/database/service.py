"""DuckDB storage service."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "data/duckdb/sigmahq.duckdb"

_VALID_TABLES = frozenset(
    {
        "config",
        "embedding_config",
        "system_prompts",
        "models",
        "doc_sigma_ref",
        "worker_state",
        "doc_registry",
        "git_metadata",
        "git_selected_dirs",
    }
)


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
        """Execute initdb.sql (schema + seed data) and apply schema migrations."""
        self._conn.execute(open("src/back/database/initdb.sql").read())
        self._conn.commit()

        # Schema migrations for existing databases
        # Add UNIQUE constraint to doc_registry if missing
        try:
            self._conn.execute(
                "ALTER TABLE doc_registry ADD CONSTRAINT uc_doc_registry UNIQUE (org, repo, content_hash)"
            )
            self._conn.commit()
        except Exception:
            pass

        # Add embed_status column to doc_sigma_ref if missing
        try:
            result = self._conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'doc_sigma_ref' AND column_name = 'embed_status'"
            ).fetchone()
            if not result:
                self._conn.execute(
                    "ALTER TABLE doc_sigma_ref ADD COLUMN embed_status TEXT DEFAULT 'pending'"
                )
                self._conn.commit()
                logger.info("Added embed_status column to doc_sigma_ref")
        except Exception as e:
            logger.warning(f"Failed to add embed_status column: {e}")

        # Add embed_status column to doc_registry if missing
        try:
            result = self._conn.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = 'doc_registry' AND column_name = 'embed_status'"
            ).fetchone()
            if not result:
                self._conn.execute(
                    "ALTER TABLE doc_registry ADD COLUMN embed_status TEXT DEFAULT 'pending'"
                )
                self._conn.commit()
                logger.info("Added embed_status column to doc_registry")
        except Exception as e:
            logger.warning(f"Failed to add embed_status column to doc_registry: {e}")

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
        return sorted(
            [
                row[0]
                for row in self._conn.execute(
                    "SELECT table_name FROM information_schema.tables WHERE table_type='BASE TABLE'"
                ).fetchall()
            ]
        )

    def get_table_data(self, table_name: str, limit: int = 50, offset: int = 0) -> list[dict]:
        """Fetch paginated data from a table."""
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
        """Return row count for a table."""
        if table_name not in _VALID_TABLES:
            raise ValueError(f"Invalid table name: {table_name}")
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
        with self._lock:
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
        with self._lock:
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
        with self._lock:
            results = self._conn.execute(
                "SELECT url_hash, original_url, normalized_url, content_type, rule_id, title, timestamp, content_sha256, embed_status FROM doc_sigma_ref ORDER BY url_hash"
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
                "embed_status": row[8],
            }
            for row in results
        ]

    def get_pending_sigma_ref(self) -> list[dict]:
        """Fetch document references pending embedding (embed_status='discovered')."""
        with self._lock:
            results = self._conn.execute(
                "SELECT url_hash, original_url, normalized_url, content_type, rule_id, title, timestamp, content_sha256, embed_status FROM doc_sigma_ref WHERE embed_status = 'discovered' ORDER BY url_hash"
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
                "embed_status": row[8],
            }
            for row in results
        ]

    def update_sigma_ref_embed_status(self, url_hash: str, status: str) -> None:
        """Update embedding status for a document reference."""
        with self._lock:
            self._conn.execute(
                "UPDATE doc_sigma_ref SET embed_status = ? WHERE url_hash = ?",
                (status, url_hash),
            )
            self._conn.commit()

    def upsert_doc_sigma_ref(self, data: dict) -> None:
        """Upsert a document reference."""
        with self._lock:
            self._conn.execute(
                """INSERT INTO doc_sigma_ref (url_hash, original_url, normalized_url, content_type, rule_id, title, timestamp, content_sha256, embed_status)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                 ON CONFLICT (url_hash) DO UPDATE SET
                     original_url = EXCLUDED.original_url,
                     normalized_url = EXCLUDED.normalized_url,
                     content_type = EXCLUDED.content_type,
                     rule_id = EXCLUDED.rule_id,
                     title = EXCLUDED.title,
                     timestamp = EXCLUDED.timestamp,
                     content_sha256 = EXCLUDED.content_sha256,
                     embed_status = EXCLUDED.embed_status""",
                (
                    data.get("url_hash"),
                    data.get("original_url"),
                    data.get("normalized_url"),
                    data.get("content_type"),
                    data.get("rule_id"),
                    data.get("title"),
                    data.get("timestamp"),
                    data.get("content_sha256"),
                    data.get("embed_status", "discovered"),
                ),
            )
            self._conn.commit()

    def doc_sigma_ref_exists(self, url_hash: str) -> bool:
        """Check if a document reference exists."""
        result = self._safe_query("SELECT 1 FROM doc_sigma_ref WHERE url_hash = ?", (url_hash,))
        return result is not None

    # =========================================================================
    # WORKER_STATE TABLE
    # =========================================================================

    def upsert_worker_state(
        self,
        worker_type: str,
        status: str = "idle",
        current_task_id: str = "",
        error: str = "",
    ) -> None:
        """Upsert worker state record."""
        with self._lock:
            self._conn.execute(
                """INSERT INTO worker_state (worker_type, status, last_heartbeat, current_task_id, started_at, error)
                 VALUES (?, ?, ?, ?, ?, ?)
                 ON CONFLICT (worker_type) DO UPDATE SET
                     status = EXCLUDED.status,
                     last_heartbeat = EXCLUDED.last_heartbeat,
                     current_task_id = EXCLUDED.current_task_id,
                     started_at = CASE WHEN EXCLUDED.started_at IS NOT NULL AND EXCLUDED.started_at != '' THEN EXCLUDED.started_at ELSE worker_state.started_at END,
                     error = EXCLUDED.error""",
                (
                    worker_type,
                    status,
                    _iso_now(),
                    current_task_id,
                    _iso_now() if status in ("running", "busy") else None,
                    error,
                ),
            )
            self._conn.commit()

    def get_worker_state(self, worker_type: str) -> dict | None:
        """Get state for a specific worker type."""
        result = self._safe_query(
            "SELECT worker_type, status, last_heartbeat, current_task_id, started_at, error FROM worker_state WHERE worker_type = ?",
            (worker_type,),
        )
        if not result:
            return None
        return {
            "worker_type": result[0],
            "status": result[1],
            "last_heartbeat": result[2],
            "current_task_id": result[3],
            "started_at": result[4],
            "error": result[5],
        }

    def get_all_worker_states(self) -> list[dict]:
        """Get state for all workers."""
        with self._lock:
            results = self._conn.execute(
                "SELECT worker_type, status, last_heartbeat, current_task_id, started_at, error FROM worker_state ORDER BY worker_type"
            ).fetchall()
        return [
            {
                "worker_type": row[0],
                "status": row[1],
                "last_heartbeat": row[2],
                "current_task_id": row[3],
                "started_at": row[4],
                "error": row[5],
            }
            for row in results
        ]

    def is_worker_busy(self, worker_type: str) -> bool:
        """Check if a worker is currently busy (running a task)."""
        result = self._safe_query(
            "SELECT 1 FROM worker_state WHERE worker_type = ? AND status IN ('running', 'busy')",
            (worker_type,),
        )
        return result is not None

    def init_worker_states(self, worker_types: list[str]) -> None:
        """Ensure all worker types exist in worker_state with idle status."""
        with self._lock:
            for wt in worker_types:
                self._conn.execute(
                    "INSERT INTO worker_state (worker_type, status, last_heartbeat, current_task_id, started_at, error) "
                    "VALUES (?, 'idle', ?, '', NULL, '') ON CONFLICT (worker_type) DO NOTHING",
                    (wt, _iso_now()),
                )
            self._conn.commit()

    def reset_stale_workers(self, stale_seconds: int = 3600) -> None:
        """Mark workers with stale heartbeats as idle."""
        from datetime import timedelta

        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=stale_seconds)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        with self._lock:
            self._conn.execute(
                """UPDATE worker_state SET status = 'idle', current_task_id = '', error = 'Heartbeat timeout', last_heartbeat = ? WHERE last_heartbeat < ? AND status IN ('running', 'busy')""",
                (_iso_now(), cutoff),
            )
            self._conn.commit()

    # =========================================================================
    # DOC_REGISTRY TABLE (File Discovery Results)
    # =========================================================================

    def upsert_doc_registry(self, data: dict) -> None:
        """Upsert a file record into doc_registry."""
        with self._lock:
            self._conn.execute(
                """INSERT INTO doc_registry (org, repo, content_type, file_name, content_hash, file_size, last_seen, status, embed_status)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                 ON CONFLICT (org, repo, content_hash) DO UPDATE SET
                     content_type = EXCLUDED.content_type,
                     file_name = EXCLUDED.file_name,
                     file_size = EXCLUDED.file_size,
                     last_seen = EXCLUDED.last_seen,
                     status = EXCLUDED.status,
                     embed_status = EXCLUDED.embed_status""",
                (
                    data.get("org"),
                    data.get("repo"),
                    data.get("content_type"),
                    data.get("file_name"),
                    data.get("content_hash"),
                    data.get("file_size"),
                    _iso_now(),
                    data.get("status", "discovered"),
                    data.get("embed_status", "discovered"),
                ),
            )
            self._conn.commit()

    def get_doc_registry(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """Fetch paginated registry records."""
        with self._lock:
            results = self._conn.execute(
                "SELECT id, org, repo, content_type, file_name, content_hash, file_size, last_seen, status, embed_status FROM doc_registry LIMIT ? OFFSET ?",
                [limit, offset],
            ).fetchall()
            col_names = [desc[0] for desc in self._conn.description]
        return [dict(zip(col_names, row)) for row in results]

    def get_pending_doc_registry(self, org: str, repo: str) -> list[dict]:
        """Fetch registry entries pending embedding for a specific repo."""
        with self._lock:
            results = self._conn.execute(
                "SELECT id, org, repo, content_type, file_name, content_hash, file_size, last_seen, status, embed_status FROM doc_registry WHERE org = ? AND repo = ? AND embed_status = 'discovered' ORDER BY id",
                (org, repo),
            ).fetchall()
            col_names = [desc[0] for desc in self._conn.description]
        return [dict(zip(col_names, row)) for row in results]

    def update_doc_registry_embed_status(self, entry_id: int, status: str) -> None:
        """Update embedding status for a registry entry."""
        with self._lock:
            self._conn.execute(
                "UPDATE doc_registry SET embed_status = ? WHERE id = ?",
                (status, entry_id),
            )
            self._conn.commit()

    def get_repos_with_selected_dirs(self) -> list[str]:
        """Get distinct repo_keys that have selected directories configured."""
        with self._lock:
            results = self._conn.execute(
                "SELECT DISTINCT repo_key FROM git_selected_dirs ORDER BY repo_key"
            ).fetchall()
        return [row[0] for row in results]

    def delete_doc_registry_by_repo(self, org: str, repo: str) -> None:
        """Clear registry records for a specific repository."""
        with self._lock:
            self._conn.execute("DELETE FROM doc_registry WHERE org = ? AND repo = ?", (org, repo))
            self._conn.commit()

    # =========================================================================
    # GIT_METADATA TABLE
    # =========================================================================

    def get_git_metadata_list(self) -> list[str]:
        """Return all repo_keys from git_metadata."""
        with self._lock:
            return [
                row[0] for row in self._conn.execute("SELECT repo_key FROM git_metadata").fetchall()
            ]

    def get_git_metadata(self, repo_key: str) -> dict | None:
        """Get metadata for a repository."""
        result = self._safe_query(
            "SELECT metadata FROM git_metadata WHERE repo_key = ?", (repo_key,)
        )
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
        with self._lock:
            results = self._conn.execute(
                "SELECT dir_path FROM git_selected_dirs WHERE repo_key = ? ORDER BY dir_path",
                (repo_key,),
            ).fetchall()
        return [row[0] for row in results]

    def set_selected_dirs(self, repo_key: str, dirs: list[str]) -> None:
        """Set selected directories for a repository."""
        now = _iso_now()
        with self._lock:
            self._conn.execute("DELETE FROM git_selected_dirs WHERE repo_key = ?", (repo_key,))
            for d in dirs:
                self._conn.execute(
                    "INSERT INTO git_selected_dirs (repo_key, dir_path, updated) VALUES (?, ?, ?)",
                    (repo_key, d, now),
                )
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
        with self._lock:
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
