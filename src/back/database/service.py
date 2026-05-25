"""DuckDB storage service — in-memory with explicit persist to disk."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger(__name__)


def _default_db_path() -> str:
    from src.shared.config import get_config

    return get_config().paths_duckdb_path


_VALID_TABLES = frozenset(
    {
        "config",
        "embedding_config",
        "system_prompts",
        "models",
        "doc_sigma_ref",
        "doc_registry",
        "git_metadata",
        "git_selected_dirs",
        "worker_state",
    }
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class DatabaseService:
    """Thread-safe DuckDB database service (in-memory) with singleton pattern.

    All operations happen in-memory for zero I/O latency. Call :meth:`persist`
    to flush the current state to disk.
    """

    _instance: DatabaseService | None = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = Path(db_path or _default_db_path())
        # Close previous singleton if re-created (e.g. hot-reload, tests)
        prev = DatabaseService._instance
        if prev is not None:
            prev.close()
        self._initialized = False
        self._writer_conn = duckdb.connect(":memory:")
        # Backward-compat alias for tests / internal access
        self._conn = self._writer_conn
        DatabaseService._instance = self
        logger.info("DatabaseService initialized in-memory (persist path: %s)", self.db_path)

    @classmethod
    def get_instance(cls) -> DatabaseService:
        if cls._instance is None:
            raise RuntimeError(
                "DatabaseService not initialized. Call main() first or run python main.py"
            )
        return cls._instance

    def initialize(self) -> None:
        """Apply schema + seed data, then load persisted data from disk (overrides seed)."""
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
        """Import data from an existing DuckDB file into the in-memory tables."""
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
        """Flush the in-memory database to a DuckDB file on disk (atomic write)."""
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
        """Close database connections and clear singleton."""
        if getattr(self, "_writer_conn", None) is not None:
            self._writer_conn.close()
            self._writer_conn = None
            self._conn = None
        DatabaseService._instance = None
        logger.info("DatabaseService closed")

    # =========================================================================
    # GENERIC TABLE OPERATIONS
    # =========================================================================

    def _get_reader_connection(self) -> duckdb.DuckDBPyConnection | None:
        """Return the shared writer connection (in-memory — no separate readers needed)."""
        return self._writer_conn

    def _safe_query(self, query: str, params: tuple = ()) -> Any:
        """Execute a read-only query with parameterized input."""
        with self._lock:
            conn = self._get_reader_connection()
            if conn is None:
                return None
            return conn.execute(query, params).fetchone()

    def get_tables(self) -> list[str]:
        """Return sorted list of valid table names."""
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
        """Fetch paginated data from a table."""
        if table_name not in _VALID_TABLES:
            raise ValueError(f"Invalid table name: {table_name}")
        limit = max(1, min(limit, 1000))
        offset = max(0, offset)
        with self._lock:
            results = self._writer_conn.execute(
                f"SELECT * FROM {table_name} LIMIT ? OFFSET ?",
                [limit, offset],
            ).fetchall()
            col_names = [desc[0] for desc in self._writer_conn.description]
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

    def set_config(self, key: str, value: dict[str, Any] | str | int | bool | None) -> None:
        """Set config value as JSON."""
        with self._lock:
            self._writer_conn.execute(
                "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (key, json.dumps(value)),
            )
            self._writer_conn.commit()

    # =========================================================================
    # MODELS TABLE
    # =========================================================================

    def get_models(self) -> list[dict]:
        """Fetch all models ordered by repo_id."""
        with self._lock:
            results = self._writer_conn.execute(
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
            self._writer_conn.execute(
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
            self._writer_conn.commit()

    def delete_model(self, repo_id: str) -> bool:
        """Delete a model by repo_id. Returns True if deleted."""
        with self._lock:
            result = self._writer_conn.execute("DELETE FROM models WHERE repo_id = ?", (repo_id,))
            self._writer_conn.commit()
            rc = result.rowcount
            return rc is not None and rc > 0

    # =========================================================================
    # SYSTEM_PROMPTS TABLE
    # =========================================================================

    def get_prompts(self) -> list[dict]:
        """Fetch all active prompts."""
        with self._lock:
            results = self._writer_conn.execute(
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
            self._writer_conn.execute(
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
            self._writer_conn.commit()

    def delete_prompt(self, prompt_id: str) -> None:
        """Delete a prompt by id."""
        with self._lock:
            self._writer_conn.execute("DELETE FROM system_prompts WHERE id = ?", (prompt_id,))
            self._writer_conn.commit()

    # =========================================================================
    # DOC_SIGMA_REF TABLE (unified document registry)
    # =========================================================================

    def get_doc_sigma_ref(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """Fetch paginated document references."""
        with self._lock:
            results = self._writer_conn.execute(
                "SELECT url_hash, org, repo, content_type, file_name, content_sha256, file_size, "
                "original_url, normalized_url, rule_id, title, timestamp, last_seen, embed_status "
                "FROM doc_sigma_ref ORDER BY url_hash LIMIT ? OFFSET ?",
                [limit, offset],
            ).fetchall()
            col_names = [desc[0] for desc in self._writer_conn.description]
        return [dict(zip(col_names, row)) for row in results]

    def get_pending_sigma_ref(self, org: str | None = None, repo: str | None = None) -> list[dict]:
        """Fetch document references pending embedding, optionally filtered by org/repo."""
        with self._lock:
            if org and repo:
                results = self._writer_conn.execute(
                    "SELECT url_hash, org, repo, content_type, file_name, content_sha256, file_size, "
                    "original_url, normalized_url, rule_id, title, timestamp, last_seen, embed_status "
                    "FROM doc_sigma_ref WHERE org = ? AND repo = ? AND embed_status = 'discovery' ORDER BY url_hash",
                    (org, repo),
                ).fetchall()
            else:
                results = self._writer_conn.execute(
                    "SELECT url_hash, org, repo, content_type, file_name, content_sha256, file_size, "
                    "original_url, normalized_url, rule_id, title, timestamp, last_seen, embed_status "
                    "FROM doc_sigma_ref WHERE embed_status = 'discovery' ORDER BY url_hash",
                ).fetchall()
            col_names = [desc[0] for desc in self._writer_conn.description]
        return [dict(zip(col_names, row)) for row in results]

    def update_sigma_ref_embed_status(self, url_hash: str, status: str) -> None:
        """Update embedding status for a document reference."""
        with self._lock:
            self._writer_conn.execute(
                "UPDATE doc_sigma_ref SET embed_status = ? WHERE url_hash = ?",
                (status, url_hash),
            )
            self._writer_conn.commit()

    def upsert_doc_sigma_ref(self, data: dict) -> None:
        """Upsert a document reference."""
        with self._lock:
            self._writer_conn.execute(
                """INSERT INTO doc_sigma_ref (
                    url_hash, org, repo, content_type, file_name, content_sha256, file_size,
                    original_url, normalized_url, rule_id, title, timestamp, last_seen, embed_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (url_hash) DO UPDATE SET
                    org = EXCLUDED.org,
                    repo = EXCLUDED.repo,
                    content_type = EXCLUDED.content_type,
                    file_name = EXCLUDED.file_name,
                    content_sha256 = EXCLUDED.content_sha256,
                    file_size = EXCLUDED.file_size,
                    original_url = EXCLUDED.original_url,
                    normalized_url = EXCLUDED.normalized_url,
                    rule_id = EXCLUDED.rule_id,
                    title = EXCLUDED.title,
                    timestamp = EXCLUDED.timestamp,
                    last_seen = EXCLUDED.last_seen,
                    embed_status = EXCLUDED.embed_status""",
                (
                    data.get("url_hash"),
                    data.get("org"),
                    data.get("repo"),
                    data.get("content_type"),
                    data.get("file_name"),
                    data.get("content_sha256"),
                    data.get("file_size"),
                    data.get("original_url"),
                    data.get("normalized_url"),
                    data.get("rule_id", "00000000-0000-0000-0000-000000000000"),
                    data.get("title"),
                    data.get("timestamp"),
                    data.get("last_seen"),
                    data.get("embed_status", "discovery"),
                ),
            )
            self._writer_conn.commit()

    def doc_sigma_ref_exists(self, url_hash: str) -> bool:
        """Check if a document reference exists."""
        result = self._safe_query("SELECT 1 FROM doc_sigma_ref WHERE url_hash = ?", (url_hash,))
        return result is not None

    def delete_doc_sigma_ref_by_repo(self, org: str, repo: str) -> None:
        """Clear document references for a specific repository."""
        with self._lock:
            self._writer_conn.execute(
                "DELETE FROM doc_sigma_ref WHERE org = ? AND repo = ?", (org, repo)
            )
            self._writer_conn.commit()

    # =========================================================================
    # DOC_REGISTRY TABLE (file discovery results from GitHub/local sources)
    # =========================================================================

    def upsert_doc_registry(self, data: dict) -> None:
        """Upsert a file record into doc_registry."""
        with self._lock:
            self._writer_conn.execute(
                """INSERT INTO doc_registry (
                    url_hash, org, repo, content_type, file_name, content_sha256, file_size,
                    original_url, normalized_url, rule_id, title, timestamp, last_seen, embed_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (url_hash) DO UPDATE SET
                    org = EXCLUDED.org,
                    repo = EXCLUDED.repo,
                    content_type = EXCLUDED.content_type,
                    file_name = EXCLUDED.file_name,
                    content_sha256 = EXCLUDED.content_sha256,
                    file_size = EXCLUDED.file_size,
                    original_url = EXCLUDED.original_url,
                    normalized_url = EXCLUDED.normalized_url,
                    rule_id = EXCLUDED.rule_id,
                    title = EXCLUDED.title,
                    timestamp = EXCLUDED.timestamp,
                    last_seen = EXCLUDED.last_seen,
                    embed_status = EXCLUDED.embed_status""",
                (
                    data.get("url_hash"),
                    data.get("org"),
                    data.get("repo"),
                    data.get("content_type"),
                    data.get("file_name"),
                    data.get("content_sha256"),
                    data.get("file_size"),
                    data.get("original_url"),
                    data.get("normalized_url"),
                    data.get("rule_id", "00000000-0000-0000-0000-000000000000"),
                    data.get("title"),
                    data.get("timestamp"),
                    data.get("last_seen"),
                    data.get("embed_status", "discovery"),
                ),
            )
            self._writer_conn.commit()

    def get_doc_registry(self, limit: int = 100, offset: int = 0) -> list[dict]:
        """Fetch paginated registry records."""
        with self._lock:
            results = self._writer_conn.execute(
                "SELECT url_hash, org, repo, content_type, file_name, content_sha256, file_size, "
                "original_url, normalized_url, rule_id, title, timestamp, last_seen, embed_status "
                "FROM doc_registry LIMIT ? OFFSET ?",
                [limit, offset],
            ).fetchall()
            col_names = [desc[0] for desc in self._writer_conn.description]
        return [dict(zip(col_names, row)) for row in results]

    def get_pending_doc_registry(self, org: str, repo: str) -> list[dict]:
        """Fetch registry entries pending embedding for a specific repo."""
        with self._lock:
            results = self._writer_conn.execute(
                "SELECT url_hash, org, repo, content_type, file_name, content_sha256, file_size, "
                "original_url, normalized_url, rule_id, title, timestamp, last_seen, embed_status "
                "FROM doc_registry WHERE org = ? AND repo = ? AND embed_status = 'discovery' ORDER BY url_hash",
                (org, repo),
            ).fetchall()
            col_names = [desc[0] for desc in self._writer_conn.description]
        return [dict(zip(col_names, row)) for row in results]

    def update_doc_registry_embed_status(self, url_hash: str, status: str) -> None:
        """Update embedding status for a registry entry."""
        with self._lock:
            self._writer_conn.execute(
                "UPDATE doc_registry SET embed_status = ? WHERE url_hash = ?",
                (status, url_hash),
            )
            self._writer_conn.commit()

    def reset_embed_status_for_collection(self, collection_name: str) -> None:
        """Reset embed_status to 'discovery' for entries linked to a Qdrant collection.

        Called after a Qdrant collection is deleted and recreated, so workers
        re-process entries whose vectors were dropped.
        """
        with self._lock:
            if collection_name == "sigmaref":
                self._writer_conn.execute(
                    "UPDATE doc_sigma_ref SET embed_status = 'discovery' WHERE org = 'sigmaref'"
                )
            elif collection_name == "local":
                self._writer_conn.execute(
                    "UPDATE doc_registry SET embed_status = 'discovery' WHERE org = 'local'"
                )
            elif "/" in collection_name:
                parts = collection_name.split("/", 2)
                if len(parts) == 2:
                    org, repo = parts
                    self._writer_conn.execute(
                        "UPDATE doc_sigma_ref SET embed_status = 'discovery' WHERE org = ? AND repo = ?",
                        (org, repo),
                    )
                    self._writer_conn.execute(
                        "UPDATE doc_registry SET embed_status = 'discovery' WHERE org = ? AND repo = ?",
                        (org, repo),
                    )
            self._writer_conn.commit()

    def delete_doc_registry_by_repo(self, org: str, repo: str) -> None:
        """Clear registry records for a specific repository."""
        with self._lock:
            self._writer_conn.execute(
                "DELETE FROM doc_registry WHERE org = ? AND repo = ?", (org, repo)
            )
            self._writer_conn.commit()

    def delete_doc_registry_by_url(self, original_url: str) -> None:
        """Delete a registry record by its original URL."""
        with self._lock:
            self._writer_conn.execute(
                "DELETE FROM doc_registry WHERE original_url = ?", (original_url,)
            )
            self._writer_conn.commit()

    def get_local_files(self, limit: int = 1000, offset: int = 0) -> list[dict]:
        """Fetch local files from doc_registry."""
        with self._lock:
            results = self._writer_conn.execute(
                "SELECT url_hash, org, repo, content_type, file_name, content_sha256, file_size, "
                "original_url, normalized_url, rule_id, title, timestamp, last_seen, embed_status "
                "FROM doc_registry WHERE org = 'local' AND repo = 'local' LIMIT ? OFFSET ?",
                [limit, offset],
            ).fetchall()
            col_names = [desc[0] for desc in self._writer_conn.description]
        return [dict(zip(col_names, row)) for row in results]

    def get_local_file_count(self) -> int:
        """Count local files in doc_registry."""
        with self._lock:
            result = self._writer_conn.execute(
                "SELECT COUNT(*) FROM doc_registry WHERE org = 'local' AND repo = 'local'"
            ).fetchone()
        return result[0]

    def resync_local_file_sizes(self, base_path: str) -> dict[str, int]:
        """Resync file_size for local files in doc_registry and doc_sigma_ref.

        Scans all local records (org='local') in both tables and updates file_size
        from the actual file on disk when file_size is NULL or 0 and the file exists.
        Also recomputes content_sha256 if missing.

        Args:
            base_path: Base path to the local documents directory.

        Returns:
            Dict with 'updated', 'skipped', 'error' counts.
        """
        updated = 0
        skipped = 0
        errors = 0
        incomplete = 0

        try:
            base_dir = Path(base_path).resolve()
        except Exception as e:
            logger.warning(f"[resync_local_file_sizes] Invalid base path '{base_path}': {e}")
            return {"updated": 0, "skipped": 0, "error": 0, "incomplete": 0}

        if not base_dir.exists():
            msg = f"[resync_local_file_sizes] Base directory does not exist: {base_dir}"
            logger.warning(msg)
            return {"updated": 0, "skipped": 0, "error": 0, "incomplete": 0}

        def _hash_file(path: Path) -> str | None:
            h = hashlib.sha256()
            try:
                with open(path, "rb") as f:
                    while True:
                        chunk = f.read(8192)
                        if not chunk:
                            break
                        h.update(chunk)
                return h.hexdigest()
            except OSError as e:
                logger.warning(f"[resync_local_file_sizes] Cannot read {path}: {e}")
                return None

        tables = ["doc_registry", "doc_sigma_ref"]

        # Phase 1: Snapshot — gather file data under lock only for SELECT (minimal critical section)
        snapshot: list[
            tuple[str, str, str | None]
        ] = []  # (table, url_hash, file_name, existing_hash)
        with self._lock:
            for table in tables:
                query = (
                    f"SELECT url_hash, file_name, content_sha256 FROM {table} "
                    "WHERE org = 'local' AND repo = 'local' "
                    "AND (file_size IS NULL OR file_size = 0) ORDER BY url_hash"
                )
                results = self._writer_conn.execute(query).fetchall()
                for row in results:
                    snapshot.append((table, row[0], row[1], row[2]))

        # Phase 2: compute sizes and hashes OUTSIDE the lock (I/O-heavy, avoid blocking writers)
        updates_by_table_col: dict[tuple[str, str], list[tuple]] = {
            ("doc_registry", "file_size"): [],
            ("doc_sigma_ref", "file_size"): [],
            ("doc_registry", "content_sha256"): [],
            ("doc_sigma_ref", "content_sha256"): [],
        }

        for table, url_hash, file_name, existing_hash in snapshot:
            if not file_name or not isinstance(file_name, str):
                skipped += 1
                continue

            try:
                file_path = (base_dir / Path(file_name)).resolve()
            except Exception:
                errors += 1
                continue

            # Fix HIGH #5: Use os.path.commonpath to avoid prefix collision
            try:
                if os.path.commonpath([str(base_dir), str(file_path)]) != str(base_dir):
                    logger.warning(
                        f"[resync_local_file_sizes] Path traversal detected for {file_name}"
                    )
                    skipped += 1
                    continue
            except ValueError:
                # commonpath raises ValueError on Windows when paths are on different drives
                logger.warning(
                    f"[resync_local_file_sizes] Cross-drive path detected for {file_name}"
                )
                skipped += 1
                continue

            try:
                stat = file_path.stat()
                new_size = stat.st_size
            except OSError as e:
                logger.warning(f"[resync_local_file_sizes] Cannot stat {file_name}: {e}")
                errors += 1
                continue

            new_hash = existing_hash
            if not existing_hash:
                computed = _hash_file(file_path)
                if computed:
                    new_hash = computed
                else:
                    logger.warning(
                        f"[resync_local_file_sizes] Hash failed for {file_name} "
                        f"(url_hash={url_hash}), file_size updated but content_sha256 unchanged"
                    )

            # Always update file_size — store actual value (0 for empty files, no sentinel)
            updates_by_table_col[(table, "file_size")].append((new_size, url_hash))

            # Only update content_sha256 if hash was computed and differs from existing
            if new_hash and new_hash != existing_hash:
                updates_by_table_col[(table, "content_sha256")].append((new_hash, url_hash))

            # Categorize the record
            if existing_hash or new_hash:
                updated += 1
            else:
                incomplete += 1

        # Phase 3: execute batched updates with transaction safety (HIGH #2)
        with self._lock:
            try:
                for (tbl, col), params in updates_by_table_col.items():
                    if params:
                        self._writer_conn.executemany(
                            f"UPDATE {tbl} SET {col} = ? WHERE url_hash = ?",
                            params,
                        )
                self._writer_conn.commit()
            except Exception as e:
                logger.error(f"[resync_local_file_sizes] Batch update failed, rolling back: {e}")

        return {"updated": updated, "skipped": skipped, "error": errors, "incomplete": incomplete}

    # =========================================================================
    # GIT_METADATA TABLE
    # =========================================================================

    def get_git_metadata_list(self) -> list[str]:
        """Return all repo_keys from git_metadata."""
        with self._lock:
            return [
                row[0]
                for row in self._writer_conn.execute("SELECT repo_key FROM git_metadata").fetchall()
            ]

    def get_git_metadata(self, repo_key: str) -> dict | None:
        """Get metadata for a repository."""
        result = self._safe_query(
            "SELECT org, name, url, branch FROM git_metadata WHERE repo_key = ?", (repo_key,)
        )
        if result:
            return {"org": result[0], "name": result[1], "url": result[2], "branch": result[3]}
        return None

    def set_git_metadata(self, repo_key: str, metadata: dict) -> None:
        """Set metadata for a repository."""
        org = metadata.get("org", "")
        name = metadata.get("name", "")
        url = metadata.get("url") or metadata.get("remote_url") or ""
        branch = metadata.get("branch", "")

        with self._lock:
            self._writer_conn.execute(
                """INSERT INTO git_metadata (repo_key, org, name, url, branch)
                   VALUES (?, ?, ?, ?, ?)
                   ON CONFLICT (repo_key) DO UPDATE SET
                       org = EXCLUDED.org,
                       name = EXCLUDED.name,
                       url = EXCLUDED.url,
                       branch = EXCLUDED.branch""",
                (repo_key, org, name, url, branch),
            )
            self._writer_conn.commit()

    def delete_git_metadata(self, repo_key: str) -> None:
        """Delete metadata for a repository."""
        with self._lock:
            self._writer_conn.execute("DELETE FROM git_metadata WHERE repo_key = ?", (repo_key,))
            self._writer_conn.commit()

    # =========================================================================
    # GIT_SELECTED_DIRS TABLE
    # =========================================================================

    def get_selected_dirs(self, repo_key: str) -> list[str]:
        """Get selected directories for a repository."""
        with self._lock:
            results = self._writer_conn.execute(
                "SELECT dir_path FROM git_selected_dirs WHERE repo_key = ? ORDER BY dir_path",
                (repo_key,),
            ).fetchall()
        return [row[0] for row in results]

    def get_repos_with_selected_dirs(self) -> list[str]:
        """Get distinct repo_keys that have selected directories configured."""
        with self._lock:
            results = self._writer_conn.execute(
                "SELECT DISTINCT repo_key FROM git_selected_dirs ORDER BY repo_key"
            ).fetchall()
        return [row[0] for row in results]

    def set_selected_dirs(self, repo_key: str, dirs: list[str]) -> None:
        """Set selected directories for a repository."""
        now = _iso_now()
        with self._lock:
            self._writer_conn.execute(
                "DELETE FROM git_selected_dirs WHERE repo_key = ?", (repo_key,)
            )
            for d in dirs:
                self._writer_conn.execute(
                    "INSERT INTO git_selected_dirs (repo_key, dir_path, updated) VALUES (?, ?, ?)",
                    (repo_key, d, now),
                )
            self._writer_conn.commit()

    def delete_selected_dirs(self, repo_key: str) -> None:
        """Delete selected directories for a repository."""
        with self._lock:
            self._writer_conn.execute(
                "DELETE FROM git_selected_dirs WHERE repo_key = ?", (repo_key,)
            )
            self._writer_conn.commit()

    # =========================================================================
    # WORKER_STATE TABLE
    # =========================================================================

    def upsert_worker_state(
        self,
        worker_type: str,
        status: str = "idle",
        current_task_id: str | None = None,
        progress_percent: float = 0.0,
        current_file: str | None = None,
    ) -> None:
        """Upsert worker state."""
        now = _iso_now()
        with self._lock:
            self._writer_conn.execute(
                """INSERT INTO worker_state (worker_type, status, current_task_id, progress_percent, current_file, last_heartbeat)
                 VALUES (?, ?, ?, ?, ?, ?)
                 ON CONFLICT (worker_type) DO UPDATE SET
                     status = EXCLUDED.status,
                     current_task_id = EXCLUDED.current_task_id,
                     progress_percent = EXCLUDED.progress_percent,
                     current_file = EXCLUDED.current_file,
                     last_heartbeat = EXCLUDED.last_heartbeat""",
                (worker_type, status, current_task_id, progress_percent, current_file, now),
            )
            self._writer_conn.commit()

    def get_worker_progress(self, worker_type: str) -> dict | None:
        """Get progress for a worker type."""
        result = self._safe_query(
            "SELECT worker_type, status, current_task_id, progress_percent, current_file, last_heartbeat FROM worker_state WHERE worker_type = ?",
            (worker_type,),
        )
        if result:
            return {
                "worker_type": result[0],
                "status": result[1],
                "current_task_id": result[2],
                "progress_percent": result[3],
                "current_file": result[4],
                "last_heartbeat": result[5],
            }
        return None

    def update_worker_progress(
        self, worker_type: str, progress_percent: float, current_file: str | None = None
    ) -> None:
        """Update progress for a worker type."""
        now = _iso_now()
        with self._lock:
            self._writer_conn.execute(
                "UPDATE worker_state SET progress_percent = ?, current_file = ?, last_heartbeat = ? WHERE worker_type = ?",
                (progress_percent, current_file, now, worker_type),
            )
            self._writer_conn.commit()

    def reset_stale_workers(self, stale_seconds: int = 60) -> None:
        """Reset workers that haven't sent a heartbeat recently."""
        from datetime import datetime, timedelta, timezone

        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=stale_seconds)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        with self._lock:
            self._writer_conn.execute(
                "UPDATE worker_state SET status = 'idle', current_task_id = NULL, progress_percent = 0.0, current_file = NULL WHERE last_heartbeat IS NOT NULL AND last_heartbeat < ?",
                (cutoff,),
            )
            self._writer_conn.commit()

    # =========================================================================
    # EMBEDDING_CONFIG TABLE (single global config)
    # =========================================================================

    def get_embedding_config(self) -> dict:
        """Get the global embedding configuration."""
        with self._lock:
            row = self._writer_conn.execute(
                "SELECT key, model FROM embedding_config LIMIT 1"
            ).fetchone()
        if row is None:
            return {}
        return {"model": row[1]}

    def set_embedding_config(self, model: str) -> None:
        """Set the global embedding model."""
        with self._lock:
            self._writer_conn.execute(
                """INSERT INTO embedding_config (key, model) VALUES ('global', ?)
                  ON CONFLICT (key) DO UPDATE SET model = EXCLUDED.model""",
                (model,),
            )
            self._writer_conn.commit()

    def delete_embedding_config(self) -> None:
        """Reset the global embedding config to default."""
        with self._lock:
            self._writer_conn.execute("DELETE FROM embedding_config WHERE key = 'global'")
            self._writer_conn.commit()
