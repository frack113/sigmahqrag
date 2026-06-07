"""Garbage collection worker â€” removes stale document entries from DuckDB."""

import logging
from pathlib import Path

from src.config.settings import get_config
from src.worker.base import BaseWorker
from src.worker.enums import WorkerName, WorkerStatus

logger = logging.getLogger(__name__)


class DocGCWorker(BaseWorker):
    """Garbage-collects document entries whose files are permanently deleted.

    Scans all non-'discovery' entries in doc_registry,
    verifies file existence on disk, and deletes definitively missing files
    after a configurable grace period.
    """

    worker_type = WorkerName.DOC_GC

    def process(self, task: dict) -> None:
        assert self.dispatcher is not None
        task_id = task.get("task_id", "")
        cfg = get_config()

        grace_days = int(task.get("grace_days", 7))
        deleted = 0
        skipped_found = 0
        scanned = 0

        self.dispatcher.update_worker_state(
            worker_type=WorkerName.DOC_GC,
            status=WorkerStatus.RUNNING,
            current_task_id=task_id,
        )

        error_msg = ""
        try:
            logger.info(
                f"[DocGCWorker] Starting GC: grace={grace_days}d, "
                f"local={cfg.local_documents_path}, sigmaref={cfg.sigmaref_documents_path}, github={cfg.paths_github_dir}"
            )

            deleted = self._gc_entries(
                table="doc_registry",
                local_base=Path(cfg.local_documents_path),
                github_base=Path(cfg.paths_github_dir),
                grace_days=grace_days,
            )

            skipped_found = self._cleanup_orphaned_error_entries()
            scanned = deleted

            logger.info(
                f"[DocGCWorker] Complete: scanned={scanned}, removed={deleted}, reappears={skipped_found}"
            )

        except Exception as e:
            error_msg = str(e)
            logger.error(f"[DocGCWorker] Failed: {e}", exc_info=True)

        self.dispatcher.update_worker_state(
            worker_type=WorkerName.DOC_GC,
            status=WorkerStatus.IDLE,
            current_task_id="",
            error=error_msg,
        )

    def _gc_entries(
        self,
        table: str,
        local_base: Path,
        github_base: Path,
        grace_days: int,
    ) -> int:
        """Scan doc_registry and delete entries for permanently deleted files."""
        deleted = 0

        try:
            with self.db._lock:
                rows = self.db._writer_conn.execute(
                    f"""SELECT url_hash, org, repo, file_name, embed_status, last_seen, content_type
                        FROM {table}
                        WHERE embed_status IN ('error', 'skipped')
                        AND last_seen < (CURRENT_TIMESTAMP - INTERVAL {grace_days} DAY)
                        ORDER BY url_hash"""
                ).fetchall()

                for row in rows:
                    url_hash, org, repo, file_name, embed_status, last_seen, content_type = row
                    scanned = self._file_exists_locally(
                        org or "",
                        repo or "",
                        file_name or "",
                        local_base,
                        github_base,
                    )

                    if scanned:
                        continue

                    with self.db._lock:
                        self.db._writer_conn.execute(
                            f"DELETE FROM {table} WHERE url_hash = ?",
                            (url_hash,),
                        )
                    deleted += 1

        except Exception as e:
            logger.error(f"[DocGCWorker] Error processing table {table}: {e}", exc_info=True)

        return deleted

    def _file_exists_locally(
        self,
        org: str,
        repo: str,
        file_name: str,
        local_base: Path,
        github_base: Path,
    ) -> bool:
        """Check if a file exists on disk under any of the known directories in doc_registry."""
        if not file_name:
            return False

        candidates: list[Path] = []

        # Case 1: local files â†’ {local_base}/{file_name}
        if org == "local":
            candidates.append(local_base / file_name)

        # Case 2: GitHub files â†’ {github_base}/{org}/{repo}/{file_name}
        if org and org not in ("local", "sigmaref") and repo:
            candidates.append(github_base / org / repo / file_name)

        # Case 3: sigmaref files ��' local base with file_name or hash prefix
        if org == "sigmaref":
            from src.config.settings import get_config

            sigmaref_base = get_config().sigmaref_documents_path
            candidates.append(Path(sigmaref_base) / file_name)
            if "." in file_name and not file_name.startswith("."):
                base, ext = file_name.rsplit(".", 1)
                if len(base) == 64:
                    candidates.append(Path(sigmaref_base) / file_name)

        for candidate in candidates:
            resolved = candidate.resolve()
            try:
                if resolved.exists() and resolved.is_file():
                    return True
            except (OSError, ValueError):
                continue

        return False

    def _cleanup_orphaned_error_entries(self) -> int:
        """Remove error entries whose URLs are no longer in doc_registry."""
        deleted = 0
        try:
            with self.db._lock:
                error_rows = self.db._writer_conn.execute(
                    "SELECT url_hash FROM doc_error ORDER BY url_hash"
                ).fetchall()

                for row in error_rows:
                    url_hash = row[0]
                    in_registry = self.db._safe_query(
                        "SELECT 1 FROM doc_registry WHERE url_hash = ?", (url_hash,)
                    )

                    if not in_registry:
                        with self.db._lock:
                            self.db._writer_conn.execute(
                                "DELETE FROM doc_error WHERE url_hash = ?",
                                (url_hash,),
                            )
                        deleted += 1

        except Exception as e:
            logger.error(f"[DocGCWorker] Error cleaning orphaned errors: {e}", exc_info=True)

        return deleted
