import logging
from pathlib import Path

from src.shared.config import get_config
from src.worker.workers.discovery_base import DiscoveryWorker
from src.back.utils.identify_file_type import SUPPORTED_DOC_EXTENSION_MAP

logger = logging.getLogger(__name__)


class LocalDiscoveryWorker(DiscoveryWorker):
    """Scans a local directory for supported documents."""

    def process(self, task: dict) -> None:
        cfg = get_config()
        config_base_path = Path(cfg.local_documents_path).resolve()
        base_path = Path(task.get("base_path", config_base_path))
        collection_name = task.get("collection_name", "local")

        logger.debug(f"[LocalDiscoveryWorker] Scanning {base_path}")

        if not base_path.exists():
            logger.warning(f"[LocalDiscoveryWorker] Path does not exist: {base_path}")
            return

        files_to_process = []
        for ext in SUPPORTED_DOC_EXTENSION_MAP.keys():
            pattern = f"**/*{ext}"
            for found_file in base_path.glob(pattern):
                files_to_process.append(found_file)

        processed_count = 0
        skipped_count = 0

        for file_path in files_to_process:
            try:
                file_rel_path = file_path.relative_to(base_path).as_posix()
                processed_count += 1

                content_hash, file_size = self._compute_sha256(file_path)
                content_type = self._identify_content_type(file_path)

                self.db.upsert_doc_registry(
                    self._make_doc_registry_entry(
                        org="local",
                        repo=collection_name,
                        file_rel_path=file_rel_path,
                        content_type=content_type,
                        content_hash=content_hash,
                        file_size=file_size,
                        original_url=f"file://{base_path}/{file_rel_path}",
                        normalized_url=f"file://{base_path}/{file_rel_path}",
                        title=file_path.stem,
                    )
                )
            except Exception as e:
                logger.error(f"[LocalDiscoveryWorker] Error processing {file_path}: {e}")
                skipped_count += 1

        logger.info(
            f"[LocalDiscoveryWorker] Complete: {processed_count} discovered, {skipped_count} skipped"
        )
