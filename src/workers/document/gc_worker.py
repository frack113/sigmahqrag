"""Garbage collection worker â€” removes stale document entries from DuckDB."""

import logging
from pathlib import Path

from src.config.settings import get_config
from src.shared.utils.identify_file_type import filetype_subdir
from src.workers.base import BaseWorker
from src.workers.enums import WorkerName, WorkerStatus

logger = logging.getLogger(__name__)


def _is_orphan_candidate(stem: str, known_hashes: set[str]) -> bool:
    """Return True if *stem* looks like a SHA256 hex hash not in *known_hashes*."""
    if len(stem) != 64:
        return False
    if not all(c in "0123456789abcdef" for c in stem):
        return False
    return stem not in known_hashes


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
                local_base=Path(cfg.local_documents_path),
                github_base=Path(cfg.paths_github_dir),
                grace_days=grace_days,
            )

            skipped_found = self._cleanup_orphaned_error_entries()

            removed_head = self.db.delete_head_verified_orphans(grace_days=grace_days)
            removed_unref = self.db.delete_unreferenced_entries()
            removed_orphan_files = self._gc_orphaned_sigmaref_files()
            removed_trash = self._cleanup_trash(Path(cfg.sigmaref_documents_path) / ".trash")

            scanned = deleted

            logger.info(
                f"[DocGCWorker] Complete: scanned={scanned}, removed={deleted}, "
                f"reappears={skipped_found}, head_verified={removed_head}, "
                f"unreferenced={removed_unref}, orphaned_files={removed_orphan_files}, "
                f"trash_cleaned={removed_trash}"
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
        local_base: Path,
        github_base: Path,
        grace_days: int,
    ) -> int:
        """Scan doc_registry and delete entries for permanently deleted files."""
        deleted = 0

        try:
            with self.db._lock:
                rows = self.db._writer_conn.execute(
                    "SELECT url_hash, org, repo, file_name, embed_status, last_seen, content_type "
                    "FROM doc_registry "
                    "WHERE embed_status IN ('error', 'skipped') "
                    "AND last_seen < (CURRENT_TIMESTAMP - INTERVAL ? DAY) "
                    "ORDER BY url_hash",
                    (grace_days,),
                ).fetchall()

                for row in rows:
                    url_hash, org, repo, file_name, embed_status, last_seen, content_type = row
                    scanned = self._file_exists_locally(
                        org or "",
                        repo or "",
                        file_name or "",
                        content_type or "",
                        local_base,
                        github_base,
                    )

                    if scanned:
                        continue

                    self.db._writer_conn.execute(
                        "DELETE FROM doc_registry WHERE url_hash = ?",
                        (url_hash,),
                    )
                    deleted += 1

        except Exception as e:
            logger.error(f"[DocGCWorker] Error processing table doc_registry: {e}", exc_info=True)

        return deleted

    def _file_exists_locally(
        self,
        org: str,
        repo: str,
        file_name: str,
        content_type: str,
        local_base: Path,
        github_base: Path,
    ) -> bool:
        """Check if a file exists on disk under any of the known directories in doc_registry."""
        if not file_name:
            return False

        candidates: list[Path] = []

        # Case 1: local files → {local_base}/{file_name}
        if org == "local":
            candidates.append(local_base / file_name)

        # Case 2: GitHub files → {github_base}/{org}/{repo}/{file_name}
        if org and org not in ("local", "sigmaref") and repo:
            candidates.append(github_base / org / repo / file_name)

        # Case 3: sigmaref files → subdir/{file_name} with flat fallback
        if org == "sigmaref":
            from src.config.settings import get_config

            sigmaref_base = get_config().sigmaref_documents_path
            subdir = filetype_subdir(content_type or "")
            candidates.append(Path(sigmaref_base) / subdir / file_name)
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

    def _gc_orphaned_sigmaref_files(self) -> int:
        """Move files in ``sigmaref/`` whose ``url_hash`` no longer exists in
        ``doc_registry`` into ``.trash/``.

        Returns the number of files removed.
        """
        cfg = get_config()
        base = Path(cfg.sigmaref_documents_path)
        if not base.exists():
            return 0

        # Collect all known sigmaref url_hashes in a single query
        known: set[str] = set()
        try:
            with self.db._lock:
                rows = self.db._writer_conn.execute(
                    "SELECT url_hash FROM doc_registry WHERE org = 'sigmaref'"
                ).fetchall()
                known = {r[0] for r in rows}
        except Exception:
            logger.warning("Failed to query doc_registry for orphaned file scan")
            return 0

        trash_dir = base / ".trash"
        removed = 0

        for entry in sorted(base.iterdir()):
            if entry.name.startswith("."):
                continue

            if entry.is_dir():
                for f in sorted(entry.iterdir()):
                    if f.is_file() and not f.name.startswith("."):
                        if _is_orphan_candidate(f.stem, known):
                            self._trash_file(f, trash_dir)
                            removed += 1
                if entry.is_dir() and not any(entry.iterdir()):
                    try:
                        entry.rmdir()
                    except OSError:
                        pass
            elif entry.is_file():
                if _is_orphan_candidate(entry.stem, known):
                    self._trash_file(entry, trash_dir)
                    removed += 1

        return removed

    def _cleanup_trash(self, trash_dir: Path, max_age_days: int = 7) -> int:
        """Permanently delete files in *trash_dir* older than *max_age_days*.

        Returns the number of files deleted.
        """
        import time

        deleted = 0
        if not trash_dir.exists():
            return 0

        cutoff = time.time() - (max_age_days * 86400)

        for entry in sorted(trash_dir.iterdir()):
            if entry.is_file() and not entry.name.startswith("."):
                try:
                    stat = entry.stat()
                    if stat.st_mtime < cutoff:
                        entry.unlink()
                        deleted += 1
                        logger.info("Permanently deleted trashed file: %s", entry)
                except OSError:
                    logger.warning("Failed to delete trashed file: %s", entry)

        # Remove empty subdirectories
        for entry in sorted(trash_dir.iterdir()):
            if entry.is_dir() and not any(entry.iterdir()):
                try:
                    entry.rmdir()
                except OSError:
                    pass

        return deleted

    def _trash_file(self, file_path: Path, trash_dir: Path) -> None:
        """Move *file_path* to *trash_dir*, skipping if already gone."""
        try:
            trash_dir.mkdir(parents=True, exist_ok=True)
            dest = trash_dir / file_path.name
            file_path.rename(dest)
            logger.info("Moved orphaned sigmaref file to trash: %s", dest)
        except OSError:
            logger.warning("Failed to move orphaned file: %s", file_path)

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
