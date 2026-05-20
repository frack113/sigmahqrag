import logging
from pathlib import Path

from src.worker.base import BaseWorker

logger = logging.getLogger(__name__)


class ModelSyncWorker(BaseWorker):
    """Syncs LLM and embedding models from filesystem into the database."""

    async def process(self, task: dict) -> None:
        task_id = task.get("task_id", "")
        llm_dir = Path(task.get("llm_dir", "data/models/llm"))
        embeddings_dir = Path(task.get("embeddings_dir", "data/models/embeddings"))

        logger.info(f"[ModelSyncWorker] Starting model sync: LLM={llm_dir}, EMBEDDINGS={embeddings_dir}")

        self.db.upsert_worker_state(
            worker_type="model_sync",
            status="running",
            current_task_id=task_id,
        )

        try:
            from src.api.dependencies import get_unified_registry

            reg = get_unified_registry()
        except Exception as e:
            logger.error(f"[ModelSyncWorker] Failed to load registry: {e}", exc_info=True)
            self.db.upsert_worker_state(
                worker_type="model_sync",
                status="idle",
                current_task_id="",
                error=f"Registry load failed: {e}",
            )
            return

        total_steps = 2
        step = 0

        try:
            logger.info("[ModelSyncWorker] Syncing LLM folder...")
            self.db.update_worker_progress(
                worker_type="model_sync",
                progress_percent=0.0,
                current_file="scanning LLM models...",
            )
            reg.sync_llm_folder(llm_dir)
            step = 1
            self.db.update_worker_progress(
                worker_type="model_sync",
                progress_percent=50.0,
                current_file="LLM models synced",
            )
            logger.info("[ModelSyncWorker] LLM folder synced.")
        except Exception as e:
            logger.error(f"[ModelSyncWorker] Failed to sync LLM folder: {e}", exc_info=True)

        try:
            logger.info("[ModelSyncWorker] Syncing embeddings folder...")
            reg.sync_embeddings_folder(embeddings_dir)
            step = 2
            self.db.update_worker_progress(
                worker_type="model_sync",
                progress_percent=100.0,
                current_file="embeddings synced",
            )
            logger.info("[ModelSyncWorker] Embeddings folder synced.")
        except Exception as e:
            logger.error(f"[ModelSyncWorker] Failed to sync embeddings folder: {e}", exc_info=True)

        self.db.upsert_worker_state(
            worker_type="model_sync",
            status="idle",
            current_task_id="",
        )
        logger.info(f"[ModelSyncWorker] Complete: {step}/{total_steps} steps done.")
