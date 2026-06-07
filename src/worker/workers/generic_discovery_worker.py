"""Unified discovery worker for all document sources."""

from __future__ import annotations

import logging
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from src.back.utils.identify_file_type import SIGMA_RULE_EXTENSIONS, SUPPORTED_DOC_EXTENSION_MAP
from src.infrastructure.database.service import DatabaseService
from src.worker.enums import WorkerName
from src.worker.workers.discovery_base import DiscoveryWorker

if TYPE_CHECKING:
    from src.worker.processor import TaskDispatcher

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = frozenset(SUPPORTED_DOC_EXTENSION_MAP.keys()) | SIGMA_RULE_EXTENSIONS


class SourceType(str, Enum):
    LOCAL = "local"
    GITHUB = "github"


class GenericDiscoveryWorker(DiscoveryWorker):
    """
    Unified discovery worker supporting multiple source types.

    Usage::

        # Local files
        GenericDiscoveryWorker(source_type=SourceType.LOCAL, base_dir=Path("/docs"))

        # GitHub repositories
        GenericDiscoveryWorker(
            source_type=SourceType.GITHUB,
            base_dir=Path("/repos"),
            github_base_dir=Path("/data/github"),
        )
    """

    def __init__(
        self,
        db: Optional["DatabaseService"] = None,
        dispatcher: Optional["TaskDispatcher"] = None,
        *,
        source_type: SourceType = SourceType.LOCAL,
        base_dir: Optional[Path] = None,
        github_base_dir: Optional[Path] = None,
        selected_dirs: Optional[list[str]] = None,
    ) -> None:
        super().__init__(db or DatabaseService.get_instance(), dispatcher)
        self.source_type = source_type
        self.base_dir = (base_dir or Path("/tmp")).resolve()
        self.github_base_dir = github_base_dir
        self.selected_dirs = selected_dirs or []

    # ------------------------------------------------------------------
    # Worker protocol
    # ------------------------------------------------------------------

    def process(self, task: dict) -> None:
        if self.source_type == SourceType.LOCAL:
            self._process_local(task, WorkerName.LOCAL_DISCOVERY)
        elif self.source_type == SourceType.GITHUB:
            self._process_github(task, WorkerName.GITHUB_DISCOVERY)
        else:
            logger.error(f"[GenericDiscoveryWorker] Unknown source type: {self.source_type!r}")

    # ------------------------------------------------------------------
    # Local source
    # ------------------------------------------------------------------

    def _process_local(self, task: dict, worker_name: WorkerName) -> None:
        from src.config.settings import get_config

        cfg = get_config()
        config_base_path = Path(cfg.local_documents_path).resolve()
        base_path = task.get("base_path") or config_base_path
        collection_name = task.get("collection_name", "local")
        scan_dir = Path(base_path)

        if not scan_dir.exists():
            logger.warning(f"[GenericDiscoveryWorker] Path does not exist: {scan_dir}")
            return

        logger.info(f"[GenericDiscoveryWorker] Scanning local: {scan_dir}")

        files_to_process: list[Path] = [
            f
            for f in scan_dir.rglob("*")
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        entries, processed_count, skipped_count = self._scan(
            scan_dir, files_to_process, org="local", repo=collection_name
        )

        self._write_entries(
            entries, worker_name, len(files_to_process), processed_count, skipped_count
        )

    # ------------------------------------------------------------------
    # GitHub source
    # ------------------------------------------------------------------

    def _process_github(self, task: dict, worker_name: WorkerName) -> None:
        gh_base = self.github_base_dir or Path(task.get("github_base_dir", "data/github"))
        gh_base = gh_base.resolve()

        try:
            repo_keys = self.db.get_repos_with_selected_dirs()
        except Exception as e:
            logger.error(f"[GenericDiscoveryWorker] Failed to query repo keys: {e}")
            return

        if not repo_keys:
            self._update_progress(worker_name, 100, "")
            logger.info("[GenericDiscoveryWorker] No repos with selected dirs")
            return

        all_files: list[tuple[Path, Path, str, str]] = []
        for repo_key in repo_keys:
            parts = repo_key.split("/")
            if len(parts) != 2:
                logger.warning(f"[GenericDiscoveryWorker] Invalid repo key: {repo_key}")
                continue

            org, repo = parts
            repo_path = gh_base / org / repo

            if not repo_path.exists():
                logger.warning(f"[GenericDiscoveryWorker] Repo not found: {repo_path}")
                continue

            selected = self.selected_dirs or self._get_selected_dirs(repo_key)

            for found_file in repo_path.rglob("*"):
                if (
                    not found_file.is_file()
                    or found_file.suffix.lower() not in SUPPORTED_EXTENSIONS
                ):
                    continue

                if selected:
                    rel_to_repo = found_file.relative_to(repo_path).as_posix()
                    if not any(
                        rel_to_repo == sd.lstrip("./")
                        or rel_to_repo.startswith(sd.lstrip("./") + "/")
                        for sd in selected
                        if sd
                    ):
                        continue

                all_files.append((found_file, repo_path, org, repo))

        if self.dispatcher:
            self._update_progress(worker_name, 1, f"{len(all_files)} files found")

        logger.info(
            f"[GenericDiscoveryWorker] Found {len(all_files)} files across {len(repo_keys)} repos"
        )

        if all_files:
            entries, processed_count, skipped_count = self._scan_all_github(all_files, worker_name)
            self._write_entries(
                entries, worker_name, len(all_files), processed_count, skipped_count
            )

    # ------------------------------------------------------------------
    # Shared scanning logic
    # ------------------------------------------------------------------

    def _scan(
        self,
        base_dir: Path,
        files: list[Path],
        org: str,
        repo: str,
    ) -> tuple[list[dict], int, int]:
        entries: list[dict] = []
        processed_count = 0
        skipped_count = 0

        for file_path in files:
            try:
                entry = self._prepare_entry(file_path, base_dir, org, repo, is_github=False)
                if entry is not None:
                    entries.append(entry)
                    processed_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                logger.error(f"[GenericDiscoveryWorker] Error processing {file_path}: {e}")
                skipped_count += 1

        return entries, processed_count, skipped_count

    def _scan_all_github(
        self,
        files: list[tuple[Path, Path, str, str]],
        worker_name: WorkerName,
    ) -> tuple[list[dict], int, int]:
        entries: list[dict] = []
        processed_count = 0
        skipped_count = 0

        for idx, (file_path, base_path, org, repo) in enumerate(files):
            try:
                entry = self._prepare_entry(file_path, base_path, org, repo, is_github=True)
                if entry is not None:
                    entries.append(entry)
                    processed_count += 1
                else:
                    skipped_count += 1
            except Exception as e:
                logger.error(f"[GenericDiscoveryWorker] Unexpected error on {file_path}: {e}")
                skipped_count += 1

            if idx % 50 == 0 and self.dispatcher:
                pct = int((idx + 1) / len(files) * 100) if files else 0
                self._update_progress(worker_name, pct, str(file_path))

        return entries, processed_count, skipped_count

    # ------------------------------------------------------------------
    # Entry preparation
    # ------------------------------------------------------------------

    def _prepare_entry(
        self,
        file_path: Path,
        base_path: Path,
        org: str,
        repo: str,
        is_github: bool = False,
    ) -> dict | None:
        try:
            if is_github:
                file_rel_path = file_path.relative_to(base_path).as_posix()
                branch = "main"
                try:
                    metadata = self.db.get_git_metadata(f"{org}/{repo}")
                    if metadata and metadata.get("branch"):
                        branch = metadata["branch"]
                except Exception:
                    pass
                original_url = f"https://github.com/{org}/{repo}/blob/{branch}/{file_rel_path}"
                normalized_url = (
                    f"https://raw.githubusercontent.com/{org}/{repo}/{branch}/{file_rel_path}"
                )
            else:
                file_rel_path = file_path.relative_to(base_path).as_posix()
                original_url = f"file://{base_path}/{file_rel_path}"
                normalized_url = original_url

            content_hash, file_size = self._compute_sha256(file_path)
            content_type = self._identify_content_type(file_path)
            title = file_path.stem

            rule_id = "00000000-0000-0000-0000-000000000000"
            if content_type == "sigma_rule":
                from src.back.utils.sigma_utils import get_sigma_rule_id

                rid = get_sigma_rule_id(file_path)
                if rid:
                    rule_id = rid

            return self._make_doc_registry_entry(
                org=org,
                repo=repo,
                file_rel_path=file_rel_path,
                content_type=content_type,
                content_hash=content_hash,
                file_size=file_size,
                original_url=original_url,
                normalized_url=normalized_url,
                title=title,
                rule_id=rule_id,
            )
        except Exception as e:
            logger.error(f"[GenericDiscoveryWorker] Cannot prepare entry for {file_path}: {e}")
            return None

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_selected_dirs(self, repo_key: str) -> list[str]:
        try:
            return self.db.get_selected_dirs(repo_key)
        except Exception as e:
            logger.error(
                f"[GenericDiscoveryWorker] Error fetching selected dirs for {repo_key}: {e}"
            )
            return []

    def _write_entries(
        self, entries: list[dict], worker_name: WorkerName, total: int, processed: int, skipped: int
    ) -> None:
        if not entries:
            self._update_progress(worker_name, 100, "")
            return

        try:
            self.db.batch_upsert_doc_registry(entries)
        except Exception as e:
            logger.error(f"[GenericDiscoveryWorker] Batch upsert failed: {e}", exc_info=True)

        if total > 0 and self.dispatcher:
            pct = int((processed + skipped) / total * 100)
            self._update_progress(worker_name, pct, "")

        self._update_progress(worker_name, 100, "")

    def _update_progress(self, worker_name: WorkerName, pct: int, current_file: str) -> None:
        if self.dispatcher:
            self.dispatcher.update_worker_state(
                worker_type=worker_name,
                progress_percent=pct,
                current_file=current_file,
            )
