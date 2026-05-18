import hashlib
import logging
from pathlib import Path

from src.back.worker.base import BaseWorker
from src.back.utils.identify_file_type import SUPPORTED_DOC_EXTENSION_MAP

logger = logging.getLogger(__name__)


class LocalDiscoveryWorker(BaseWorker):
    """Scans a local directory for supported documents.

    TODO: Complete implementation for next branch.
    - Support configurable base_path via task params
    - Support file type filtering
    - Handle symlinks and excluded patterns
    """

    async def process(self, task: dict) -> None:
        task_id = task["task_id"]
        base_path = Path(task.get("base_path", "data/documents/local"))
        collection_name = task.get("collection_name", "local")

        logger.info(f"[LocalDiscoveryWorker] Scanning {base_path} (WIP)")

        if not base_path.exists():
            logger.warning(f"[LocalDiscoveryWorker] Path does not exist: {base_path}")
            self.db.upsert_embed_progress(
                task_id=task_id,
                status="completed",
                source_type="local_discovery",
                total=0,
                processed=0,
                skipped=0,
                collection_name=collection_name,
                progress_percent=100.0,
                current_file="path not found",
            )
            return

        self.db.upsert_embed_progress(
            task_id=task_id,
            status="running",
            source_type="local_discovery",
            collection_name=collection_name,
            current_file="scanning local directory...",
        )

        files_to_process = []
        for ext in SUPPORTED_DOC_EXTENSION_MAP.keys():
            pattern = f"**/*.{ext}"
            for found_file in base_path.glob(pattern):
                files_to_process.append(found_file)

        total_files = len(files_to_process)
        processed_count = 0
        skipped_count = 0

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

                content_type = file_path.suffix.lower().lstrip(".")

                self.db.upsert_doc_registry({
                    "org": "local",
                    "repo": collection_name,
                    "content_type": content_type,
                    "file_name": file_rel_path,
                    "content_hash": content_hash,
                    "file_size": file_size,
                    "status": "discovered",
                })

                self.db.upsert_embed_progress(
                    task_id=task_id,
                    status="running",
                    source_type="local_discovery",
                    total=total_files,
                    processed=processed_count,
                    skipped=skipped_count,
                    current_file=file_rel_path,
                    collection_name=collection_name,
                    progress_percent=percent,
                )
            except Exception as e:
                logger.error(f"[LocalDiscoveryWorker] Error processing {file_path}: {e}")
                skipped_count += 1

        self.db.upsert_embed_progress(
            task_id=task_id,
            status="completed",
            source_type="local_discovery",
            total=total_files,
            processed=processed_count,
            skipped=skipped_count,
            collection_name=collection_name,
            progress_percent=100.0,
            current_file=f"{processed_count} files discovered",
        )

        logger.info(
            f"[LocalDiscoveryWorker] Complete: {processed_count} discovered, {skipped_count} skipped"
        )
