import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from src.back.worker.base import BaseWorker
from src.back.utils.identify_file_type import SUPPORTED_DOC_EXTENSION_MAP, identify

logger = logging.getLogger(__name__)


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class LocalDiscoveryWorker(BaseWorker):
    """Scans a local directory for supported documents."""

    async def process(self, task: dict) -> None:
        base_path = Path(task.get("base_path", "data/documents/local"))
        collection_name = task.get("collection_name", "local")

        logger.info(f"[LocalDiscoveryWorker] Scanning {base_path} (WIP)")

        if not base_path.exists():
            logger.warning(f"[LocalDiscoveryWorker] Path does not exist: {base_path}")
            return

        files_to_process = []
        for ext in SUPPORTED_DOC_EXTENSION_MAP.keys():
            pattern = f"**/*.{ext}"
            for found_file in base_path.glob(pattern):
                files_to_process.append(found_file)

        processed_count = 0
        skipped_count = 0

        for file_path in files_to_process:
            try:
                file_rel_path = file_path.relative_to(base_path).as_posix()
                processed_count += 1

                try:
                    file_bytes = file_path.read_bytes()
                    content_hash = hashlib.sha256(file_bytes).hexdigest()
                    file_size = file_path.stat().st_size
                except Exception:
                    content_hash = ""
                    file_size = 0

                content_type = identify(file_path).value
                url_hash = hashlib.sha256(
                    f"local/{collection_name}/{file_rel_path}".encode()
                ).hexdigest()
                title = file_path.stem

                self.db.upsert_doc_sigma_ref(
                    {
                        "url_hash": url_hash,
                        "org": "local",
                        "repo": collection_name,
                        "content_type": content_type,
                        "file_name": file_rel_path,
                        "content_sha256": content_hash,
                        "file_size": file_size,
                        "original_url": f"file://{base_path}/{file_rel_path}",
                        "normalized_url": f"file://{base_path}/{file_rel_path}",
                        "rule_id": "00000000-0000-0000-0000-000000000000",
                        "title": title,
                        "timestamp": _iso_now(),
                        "last_seen": _iso_now(),
                        "status": "discovered",
                        "embed_status": "discovery",
                    }
                )
            except Exception as e:
                logger.error(f"[LocalDiscoveryWorker] Error processing {file_path}: {e}")
                skipped_count += 1

        logger.info(
            f"[LocalDiscoveryWorker] Complete: {processed_count} discovered, {skipped_count} skipped"
        )
