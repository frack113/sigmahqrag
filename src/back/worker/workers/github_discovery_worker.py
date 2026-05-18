import hashlib
import logging
from pathlib import Path

from src.back.worker.base import BaseWorker
from src.back.utils.identify_file_type import SUPPORTED_DOC_EXTENSION_MAP

logger = logging.getLogger(__name__)


class GithubDiscoveryWorker(BaseWorker):
    """Scans cloned GitHub repositories for supported documents."""

    async def process(self, task: dict) -> None:
        task_id = task["task_id"]
        collection_name = task.get("collection_name", "")
        org = task.get("org", "")
        repo = task.get("repo", "")

        if not collection_name:
            raise ValueError("collection_name is required for github discovery")

        parts = collection_name.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid collection name for github discovery: {collection_name}")

        org = parts[0]
        repo = parts[1]
        base_path = Path("data/github") / org / repo

        if not base_path.exists():
            raise FileNotFoundError(f"Repository path does not exist: {base_path}")

        logger.info(f"[GithubDiscoveryWorker] Scanning {collection_name} in {base_path}")

        self.db.upsert_embed_progress(
            task_id=task_id,
            status="running",
            source_type="github_discovery",
            collection_name=collection_name,
            current_file="scanning repository...",
        )

        selected_dirs = []
        try:
            selected_dirs = self.db.get_selected_dirs(collection_name)
            logger.info(
                f"[GithubDiscoveryWorker] {collection_name} has {len(selected_dirs)} selected directories."
            )
        except Exception as e:
            logger.error(f"[GithubDiscoveryWorker] Error fetching selected dirs: {e}")

        files_to_process = []
        for ext in SUPPORTED_DOC_EXTENSION_MAP.keys():
            pattern = f"**/*.{ext}"
            for found_file in base_path.glob(pattern):
                if selected_dirs:
                    rel_to_repo = found_file.relative_to(base_path).as_posix()
                    if any(rel_to_repo.startswith(sd.lstrip("./")) for sd in selected_dirs):
                        files_to_process.append(found_file)
                else:
                    files_to_process.append(found_file)

        total_files = len(files_to_process)
        processed_count = 0
        skipped_count = 0

        self.db.upsert_embed_progress(
            task_id=task_id,
            status="running",
            source_type="github_discovery",
            total=total_files,
            processed=0,
            collection_name=collection_name,
            current_file=f"found {total_files} files",
        )

        for file_path in files_to_process:
            try:
                file_rel_path = file_path.relative_to(base_path).as_posix()
                processed_count += 1
                percent = (processed_count / total_files) * 100 if total_files > 0 else 100

                try:
                    file_bytes = file_path.read_bytes()
                    content_hash = hashlib.sha256(file_bytes).hexdigest()
                    file_size = file_path.stat().st_size
                except Exception:
                    content_hash = ""
                    file_size = 0

                rel_lower = file_rel_path.lower()
                if rel_lower.startswith("rules") or "/rules/" in rel_lower:
                    content_type = "rules"
                elif rel_lower.startswith("specification") or "/specification/" in rel_lower:
                    content_type = "specification"
                else:
                    content_type = file_path.suffix.lower().lstrip(".")

                self.db.upsert_doc_registry(
                    {
                        "org": org,
                        "repo": repo,
                        "content_type": content_type,
                        "file_name": file_rel_path,
                        "content_hash": content_hash,
                        "file_size": file_size,
                        "status": "discovered",
                    }
                )

                self.db.upsert_embed_progress(
                    task_id=task_id,
                    status="running",
                    source_type="github_discovery",
                    total=total_files,
                    processed=processed_count,
                    skipped=skipped_count,
                    current_file=file_rel_path,
                    collection_name=collection_name,
                    progress_percent=percent,
                )
            except Exception as e:
                logger.error(f"[GithubDiscoveryWorker] Error processing {file_path}: {e}")
                skipped_count += 1

        self.db.upsert_embed_progress(
            task_id=task_id,
            status="completed",
            source_type="github_discovery",
            total=total_files,
            processed=processed_count,
            skipped=skipped_count,
            collection_name=collection_name,
            progress_percent=100.0,
            current_file=f"{processed_count} files discovered",
        )

        logger.info(
            f"[GithubDiscoveryWorker] Complete: {processed_count} discovered, {skipped_count} skipped"
        )
