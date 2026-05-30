import logging
from pathlib import Path

from src.worker.workers.discovery_base import DiscoveryWorker
from src.back.utils.identify_file_type import SUPPORTED_DOC_EXTENSION_MAP

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = frozenset(SUPPORTED_DOC_EXTENSION_MAP.keys())


class GithubDiscoveryWorker(DiscoveryWorker):
    """Scans all cloned GitHub repositories with selected directories for supported documents."""

    github_base_dir: str = ""
    default_branch: str = "main"

    def _build_urls(self, org: str, repo: str, file_rel_path: str) -> tuple[str, str]:
        """Build original and normalized URLs for a file."""
        branch = self.default_branch
        try:
            metadata = self.db.get_git_metadata(f"{org}/{repo}")
            if metadata and metadata.get("branch"):
                branch = metadata["branch"]
        except Exception:
            pass

        original_url = f"https://github.com/{org}/{repo}/blob/{branch}/{file_rel_path}"
        normalized_url = f"https://raw.githubusercontent.com/{org}/{repo}/{branch}/{file_rel_path}"
        return original_url, normalized_url

    def _prepare_entry(self, file_path: Path, base_path: Path, org: str, repo: str) -> dict | None:
        """Prepare a doc_registry entry for a single file. Returns None on error."""
        try:
            file_rel_path = file_path.relative_to(base_path).as_posix()
        except ValueError as e:
            logger.error(f"[GithubDiscoveryWorker] Cannot relativize {file_path}: {e}")
            return None

        content_hash, file_size = self._compute_sha256(file_path)
        content_type = self._identify_content_type(file_path)
        original_url, normalized_url = self._build_urls(org, repo, file_rel_path)
        title = file_path.stem

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
        )

    def process(self, task: dict) -> None:
        from src.shared.config import get_config
        from src.worker.enums import WorkerName

        base_dir = task.get("github_base_dir") or get_config().paths_github_dir or "data/github"

        try:
            repo_keys = self.db.get_repos_with_selected_dirs()
            if not repo_keys:
                if self.dispatcher is not None:
                    self.dispatcher.update_worker_state(
                        WorkerName.GITHUB_DISCOVERY,
                        progress_percent=100,
                        current_file="",
                    )
                logger.info("[GithubDiscoveryWorker] No repos with selected dirs, nothing to scan")
                return

            all_files: list[tuple[Path, Path, str, str]] = []
            for repo_key in repo_keys:
                parts = repo_key.split("/")
                if len(parts) != 2:
                    logger.warning(f"[GithubDiscoveryWorker] Invalid repo key: {repo_key}")
                    continue

                org, repo = parts
                base_path = Path(base_dir) / org / repo
                if not base_path.exists():
                    logger.warning(f"[GithubDiscoveryWorker] Repo not found: {base_path}")
                    continue

                selected_dirs = []
                try:
                    selected_dirs = self.db.get_selected_dirs(repo_key)
                except Exception as e:
                    logger.error(
                        f"[GithubDiscoveryWorker] Error fetching selected dirs for {repo_key}: {e}"
                    )

                for found_file in base_path.rglob("*"):
                    if found_file.is_file() and found_file.suffix.lower() in SUPPORTED_EXTENSIONS:
                        if selected_dirs:
                            rel_to_repo = found_file.relative_to(base_path).as_posix()
                            if not any(
                                rel_to_repo.startswith(sd.lstrip("./")) for sd in selected_dirs
                            ):
                                continue
                        all_files.append((found_file, base_path, org, repo))

            total_files = len(all_files)
            processed_count = 0
            skipped_count = 0

            logger.info(
                f"[GithubDiscoveryWorker] Found {total_files} files across {len(repo_keys)} repos"
            )

            all_entries: list[dict] = []
            for file_path, base_path, org, repo in all_files:
                try:
                    entry = self._prepare_entry(file_path, base_path, org, repo)
                    if entry is not None:
                        all_entries.append(entry)
                        processed_count += 1
                    else:
                        skipped_count += 1
                except Exception as e:
                    logger.error(
                        f"[GithubDiscoveryWorker] Unexpected error on {file_path}: {e}",
                        exc_info=True,
                    )
                    skipped_count += 1

            if all_entries:
                try:
                    self.db.batch_upsert_doc_registry(all_entries)
                except Exception as e:
                    logger.error(f"[GithubDiscoveryWorker] Batch upsert failed: {e}", exc_info=True)

                if total_files > 0 and self.dispatcher is not None:
                    pct = int((processed_count + skipped_count) / total_files * 100)
                    self.dispatcher.update_worker_state(
                        WorkerName.GITHUB_DISCOVERY,
                        progress_percent=pct,
                        current_file=str(file_path),
                    )

            if self.dispatcher is not None:
                self.dispatcher.update_worker_state(
                    WorkerName.GITHUB_DISCOVERY,
                    progress_percent=100,
                    current_file="",
                )
            logger.info(
                f"[GithubDiscoveryWorker] Complete: {processed_count} discovered, {skipped_count} skipped"
            )
        except Exception as e:
            logger.error(f"[GithubDiscoveryWorker] FATAL error in process(): {e}", exc_info=True)
            raise
