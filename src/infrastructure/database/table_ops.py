"""DuckDB table operations — models, prompts, git, worker, embedding_config."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import threading

    import duckdb

from src.shared.utils import iso_now

logger = logging.getLogger(__name__)


class DatabaseServiceTableOps:
    """Table-specific operations (models, system_prompts, git, worker_state, embedding_config)."""

    # Provided by DatabaseServiceCore mixin
    _lock: threading.RLock
    _writer_conn: duckdb.DuckDBPyConnection

    def _safe_query(self, query: str, params: tuple = ()) -> Any: ...

    # ------------------------------------------------------------------
    # MODELS table
    # ------------------------------------------------------------------

    def get_models(self) -> list[dict]:
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
        with self._lock:
            result = self._writer_conn.execute("DELETE FROM models WHERE repo_id = ?", (repo_id,))
            self._writer_conn.commit()
            rc = result.rowcount
            return rc is not None and rc > 0

    # ------------------------------------------------------------------
    # SYSTEM_PROMPTS table
    # ------------------------------------------------------------------

    def get_prompts(self) -> list[dict]:
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
        with self._lock:
            self._writer_conn.execute("DELETE FROM system_prompts WHERE id = ?", (prompt_id,))
            self._writer_conn.commit()

    # ------------------------------------------------------------------
    # GIT_METADATA table
    # ------------------------------------------------------------------

    def get_git_metadata_list(self) -> list[str]:
        with self._lock:
            return [
                row[0]
                for row in self._writer_conn.execute("SELECT repo_key FROM git_metadata").fetchall()
            ]

    def get_git_metadata(self, repo_key: str) -> dict | None:
        result = self._safe_query(
            "SELECT org, name, url, branch FROM git_metadata WHERE repo_key = ?", (repo_key,)
        )
        if result:
            return {"org": result[0], "name": result[1], "url": result[2], "branch": result[3]}
        return None

    def set_git_metadata(self, repo_key: str, metadata: dict) -> None:
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
        with self._lock:
            self._writer_conn.execute("DELETE FROM git_metadata WHERE repo_key = ?", (repo_key,))
            self._writer_conn.commit()

    # ------------------------------------------------------------------
    # GIT_SELECTED_DIRS table
    # ------------------------------------------------------------------

    def get_selected_dirs(self, repo_key: str) -> list[str]:
        with self._lock:
            results = self._writer_conn.execute(
                "SELECT dir_path FROM git_selected_dirs WHERE repo_key = ? ORDER BY dir_path",
                (repo_key,),
            ).fetchall()
        return [row[0] for row in results]

    def get_repos_with_selected_dirs(self) -> list[str]:
        with self._lock:
            results = self._writer_conn.execute(
                "SELECT DISTINCT repo_key FROM git_selected_dirs ORDER BY repo_key"
            ).fetchall()
        return [row[0] for row in results]

    def set_selected_dirs(self, repo_key: str, dirs: list[str]) -> None:
        with self._lock:
            self._writer_conn.execute(
                "DELETE FROM git_selected_dirs WHERE repo_key = ?", (repo_key,)
            )
            for d in dirs:
                self._writer_conn.execute(
                    "INSERT INTO git_selected_dirs (repo_key, dir_path, updated) VALUES (?, ?, ?)",
                    (repo_key, d, iso_now()),
                )
            self._writer_conn.commit()

    def delete_selected_dirs(self, repo_key: str) -> None:
        with self._lock:
            self._writer_conn.execute(
                "DELETE FROM git_selected_dirs WHERE repo_key = ?", (repo_key,)
            )
            self._writer_conn.commit()

    # ------------------------------------------------------------------
    # WORKER_STATE table
    # ------------------------------------------------------------------

    def upsert_worker_state(
        self,
        worker_type: str,
        status: str = "idle",
        current_task_id: str | None = None,
        progress_percent: float = 0.0,
        current_file: str | None = None,
    ) -> None:
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
                (worker_type, status, current_task_id, progress_percent, current_file, iso_now()),
            )
            self._writer_conn.commit()

    def get_worker_progress(self, worker_type: str) -> dict | None:
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
        with self._lock:
            self._writer_conn.execute(
                "UPDATE worker_state SET progress_percent = ?, current_file = ?, last_heartbeat = ? WHERE worker_type = ?",
                (progress_percent, current_file, iso_now(), worker_type),
            )
            self._writer_conn.commit()

    def reset_stale_workers(self, stale_seconds: int = 60) -> None:
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=stale_seconds)).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        with self._lock:
            self._writer_conn.execute(
                "UPDATE worker_state SET status = 'idle', current_task_id = NULL, progress_percent = 0.0, current_file = NULL WHERE last_heartbeat IS NOT NULL AND last_heartbeat < ?",
                (cutoff,),
            )
            self._writer_conn.commit()

    # ------------------------------------------------------------------
    # EMBEDDING_CONFIG table (single global config)
    # ------------------------------------------------------------------

    def get_embedding_config(self) -> dict:
        with self._lock:
            row = self._writer_conn.execute(
                "SELECT key, model FROM embedding_config LIMIT 1"
            ).fetchone()
        if row is None:
            return {}
        return {"model": row[1]}

    def set_embedding_config(self, model: str) -> None:
        with self._lock:
            self._writer_conn.execute(
                """INSERT INTO embedding_config (key, model) VALUES ('global', ?)
                  ON CONFLICT (key) DO UPDATE SET model = EXCLUDED.model""",
                (model,),
            )
            self._writer_conn.commit()

    def delete_embedding_config(self) -> None:
        with self._lock:
            self._writer_conn.execute("DELETE FROM embedding_config WHERE key = 'global'")
            self._writer_conn.commit()
