import asyncio
import hashlib
import logging
from pathlib import Path

from src.worker.base import BaseWorker
from src.worker.utils import iso_now
from src.back.utils.identify_file_type import SUPPORTED_DOC_EXTENSION_MAP, identify

logger = logging.getLogger(__name__)


class GithubDiscoveryWorker(BaseWorker):
    """Scans all cloned GitHub repositories with selected directories for supported documents."""

    github_base_dir: str = "data/github"
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

    def _process_file(
        self, file_path: Path, base_path: Path, org: str, repo: str
    ) -> bool:
        """Process a single file and register it in the database. Returns True on success."""
        logger.info(f"[GithubDiscoveryWorker] _process_file ENTER: {file_path.name}")
        try:
            file_rel_path = file_path.relative_to(base_path).as_posix()
            logger.info(f"[GithubDiscoveryWorker] relative_to OK: {file_rel_path}")
        except ValueError as e:
            logger.error(f"[GithubDiscoveryWorker] Cannot relativize {file_path}: {e}")
            return False

        try:
            file_bytes = file_path.read_bytes()
            content_hash = hashlib.sha256(file_bytes).hexdigest()
            file_size = file_path.stat().st_size
            logger.info(f"[GithubDiscoveryWorker] read_bytes OK: {file_size} bytes")
        except Exception as e:
            logger.warning(f"[GithubDiscoveryWorker] Cannot read {file_path}: {e}")
            content_hash = ""
            file_size = 0

        try:
            content_type = identify(file_path).value
            logger.info(f"[GithubDiscoveryWorker] identify OK: {content_type}")
        except Exception as e:
            logger.warning(f"[GithubDiscoveryWorker] Cannot identify {file_path}: {e}")
            content_type = "unknown"

        original_url, normalized_url = self._build_urls(org, repo, file_rel_path)
        url_hash = hashlib.sha256(normalized_url.encode()).hexdigest()
        title = file_path.stem

        logger.info(f"[GithubDiscoveryWorker] About to call upsert_doc_registry for {file_rel_path}")
        try:
            self.db.upsert_doc_registry(
                {
                    "url_hash": url_hash,
                    "org": org,
                    "repo": repo,
                    "content_type": content_type,
                    "file_name": file_rel_path,
                    "content_sha256": content_hash,
                    "file_size": file_size,
                    "original_url": original_url,
                    "normalized_url": normalized_url,
                    "rule_id": "00000000-0000-0000-0000-000000000000",
                    "title": title,
                    "timestamp": iso_now(),
                    "last_seen": iso_now(),
                    "embed_status": "discovered",
                }
            )
            logger.info(f"[GithubDiscoveryWorker] upsert_doc_registry RETURNED OK for {file_rel_path}")
            return True
        except Exception as e:
            logger.error(f"[GithubDiscoveryWorker] DB error for {file_rel_path}: {e}", exc_info=True)
            return False

    async def process(self, task: dict) -> None:
        try:
            repo_keys = self.db.get_repos_with_selected_dirs()
            if not repo_keys:
                logger.info("[GithubDiscoveryWorker] No repos with selected dirs, nothing to scan")
                return

            all_files: list[tuple[Path, Path, str, str]] = []
            for repo_key in repo_keys:
                parts = repo_key.split("/")
                if len(parts) != 2:
                    logger.warning(f"[GithubDiscoveryWorker] Invalid repo key: {repo_key}")
                    continue

                org, repo = parts
                base_path = Path(self.github_base_dir) / org / repo
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

                for ext in SUPPORTED_DOC_EXTENSION_MAP.keys():
                    pattern = f"**/*{ext}"
                    for found_file in base_path.glob(pattern):
                        if selected_dirs:
                            rel_to_repo = found_file.relative_to(base_path).as_posix()
                            if not any(rel_to_repo.startswith(sd.lstrip("./")) for sd in selected_dirs):
                                continue
                        all_files.append((found_file, base_path, org, repo))

            total_files = len(all_files)
            processed_count = 0
            skipped_count = 0

            logger.info(
                f"[GithubDiscoveryWorker] Found {total_files} files across {len(repo_keys)} repos"
            )

            # Yield to event loop before starting DB-heavy work
            await asyncio.sleep(0)

            for idx, (file_path, base_path, org, repo) in enumerate(all_files):
                logger.info(f"[GithubDiscoveryWorker] Processing [{idx + 1}/{total_files}] {file_path.name}")
                try:
                    if self._process_file(file_path, base_path, org, repo):
                        processed_count += 1
                    else:
                        skipped_count += 1
                    logger.debug(
                        f"[GithubDiscoveryWorker] [{idx + 1}/{total_files}] {file_path.name}"
                    )
                    await asyncio.sleep(0)
                except Exception as e:
                    logger.error(
                        f"[GithubDiscoveryWorker] Unexpected error on file {idx+1}/{total_files} {file_path}: {e}",
                        exc_info=True,
                    )
                    skipped_count += 1

            logger.info(
                f"[GithubDiscoveryWorker] Complete: {processed_count} discovered, {skipped_count} skipped"
            )
        except Exception as e:
            logger.error(f"[GithubDiscoveryWorker] FATAL error in process(): {e}", exc_info=True)
            raise
