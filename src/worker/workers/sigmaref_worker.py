"""Worker that processes Sigma rules in doc_registry and downloads their reference documents."""

from __future__ import annotations

import logging

from src.application.documents.sigma_ref_processor import process_sigma_refs
from src.shared.utils.identify_file_type import SUPPORTED_REFERENCE_DOC_TYPES
from src.config.settings import get_config
from src.worker.base import BaseWorker
from src.worker.enums import WorkerName, WorkerStatus

logger = logging.getLogger(__name__)


class SigmaRefProcessor(BaseWorker):
    """Downloads reference documents for Sigma rules already in doc_registry."""

    worker_type = WorkerName.SIGMAREF_DISCOVERY

    def process(self, task: dict) -> None:
        dispatcher = self.dispatcher
        assert dispatcher is not None
        cfg = get_config()
        output_dir = task.get("output_dir") or str(cfg.sigmaref_documents_path)

        logger.info(f"[SigmaRefProcessor] Starting: output_dir={output_dir}")

        def _on_progress(current: int, total: int, phase: str) -> None:
            if total == 0:
                return
            pct = round((current / total) * 100, 1)
            dispatcher.update_worker_state(
                worker_type=self.worker_type,
                status=WorkerStatus.RUNNING,
                progress_percent=pct,
                current_file=f"{phase}: {current}/{total}",
            )

        try:
            summary = process_sigma_refs(
                db=self.db,
                output_dir=output_dir,
                supported_types=SUPPORTED_REFERENCE_DOC_TYPES,
                progress_callback=_on_progress,
            )
            logger.info(f"[SigmaRefProcessor] Complete: {summary}")
        except Exception as e:
            logger.error(f"[SigmaRefProcessor] Failed: {e}", exc_info=True)
            raise


# Backwards alias
SigmaRefWorker = SigmaRefProcessor
