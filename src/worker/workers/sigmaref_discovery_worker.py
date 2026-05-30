import logging

from src.shared.config import get_config
from src.worker.base import BaseWorker
from src.worker.enums import WorkerName, WorkerStatus
from src.back.documents.sigma_ref_downloader import download_references
from src.back.utils.identify_file_type import SUPPORTED_REFERENCE_DOC_TYPES

logger = logging.getLogger(__name__)


class SigmaRefDiscoveryWorker(BaseWorker):
    worker_type = WorkerName.SIGMAREF_DISCOVERY
    """Scans Sigma rule YAML files, extracts reference URLs, and downloads them."""

    def process(self, task: dict) -> None:
        dispatcher = self.dispatcher
        assert dispatcher is not None
        cfg = get_config()
        rules_dir = task.get("rules_dir", cfg.paths_github_dir)
        output_dir = task.get("output_dir") or str(cfg.sigmaref_documents_path)

        logger.info(
            f"[SigmaRefDiscoveryWorker] Starting discovery: rules={rules_dir}, output={output_dir}"
        )

        def _on_progress(current: int, total: int, phase: str) -> None:
            pct = round((current / total) * 100, 1)
            dispatcher.update_worker_state(
                worker_type=self.worker_type,
                status=WorkerStatus.RUNNING,
                progress_percent=pct,
                current_file=f"{phase}: {current}/{total}",
            )

        try:
            summary = download_references(
                rules_dir=rules_dir,
                output_dir=output_dir,
                db=self.db,
                supported_types=SUPPORTED_REFERENCE_DOC_TYPES,
                progress_callback=_on_progress,
            )
            logger.info(f"[SigmaRefDiscoveryWorker] Complete: {summary}")
        except Exception as e:
            logger.error(f"[SigmaRefDiscoveryWorker] Failed: {e}", exc_info=True)
            raise
