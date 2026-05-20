import logging

from src.worker.base import BaseWorker
from src.back.documents.sigma_ref_downloader import download_references

logger = logging.getLogger(__name__)


class SigmaRefDiscoveryWorker(BaseWorker):
    """Scans Sigma rule YAML files, extracts reference URLs, and downloads them."""

    async def process(self, task: dict) -> None:
        rules_dir = task.get("rules_dir", "data/rules")
        output_dir = task.get("output_dir", "data/documents/sigmaref")

        logger.info(
            f"[SigmaRefDiscoveryWorker] Starting discovery: rules={rules_dir}, output={output_dir}"
        )

        try:
            summary = download_references(
                rules_dir=rules_dir,
                output_dir=output_dir,
                supported_types={"markdown"},
            )
            logger.info(f"[SigmaRefDiscoveryWorker] Complete: {summary}")
        except Exception as e:
            logger.error(f"[SigmaRefDiscoveryWorker] Failed: {e}", exc_info=True)
            raise
