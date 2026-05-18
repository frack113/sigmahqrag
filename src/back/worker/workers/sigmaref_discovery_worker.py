import logging

from src.back.worker.base import BaseWorker
from src.back.documents.sigma_ref_downloader import download_references

logger = logging.getLogger(__name__)


class SigmaRefDiscoveryWorker(BaseWorker):
    """Scans Sigma rule YAML files, extracts reference URLs, and downloads them."""

    async def process(self, task: dict) -> None:
        task_id = task["task_id"]
        rules_dir = task.get("rules_dir", "data/rules")
        output_dir = task.get("output_dir", "data/documents/sigmaref")
        collection_name = task.get("collection_name", "sigmaref")

        logger.info(
            f"[SigmaRefDiscoveryWorker] Starting discovery: rules={rules_dir}, output={output_dir}"
        )

        self.db.upsert_embed_progress(
            task_id=task_id,
            status="running",
            source_type="sigmaref_discovery",
            collection_name=collection_name,
            current_file="scanning rules...",
        )

        summary = download_references(
            rules_dir=rules_dir,
            output_dir=output_dir,
            supported_types={"markdown"},
        )

        total = summary.get("total_refs", 0)
        downloaded = summary.get("downloaded", 0)
        skipped = summary.get("skipped", 0)
        failed = summary.get("failed", 0)

        if failed > 0:
            self.db.upsert_embed_progress(
                task_id=task_id,
                status="completed",
                source_type="sigmaref_discovery",
                total=total,
                processed=downloaded,
                skipped=skipped,
                errors=f"{failed} downloads failed",
                collection_name=collection_name,
                progress_percent=100.0,
                current_file=f"{downloaded} downloaded, {skipped} skipped, {failed} failed",
            )
        else:
            self.db.upsert_embed_progress(
                task_id=task_id,
                status="completed",
                source_type="sigmaref_discovery",
                total=total,
                processed=downloaded,
                skipped=skipped,
                collection_name=collection_name,
                progress_percent=100.0,
                current_file=f"{downloaded} downloaded, {skipped} skipped",
            )

        logger.info(f"[SigmaRefDiscoveryWorker] Complete: {summary}")
