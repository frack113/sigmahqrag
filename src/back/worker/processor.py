import asyncio
import logging
from typing import Dict, Type

from src.back.database.service import DatabaseService
from src.back.worker.base import BaseWorker
from src.back.worker.workers.github_discovery_worker import GithubDiscoveryWorker
from src.back.worker.workers.github_embedding_worker import GithubEmbeddingWorker
from src.back.worker.workers.local_discovery_worker import LocalDiscoveryWorker
from src.back.worker.workers.local_embedding_worker import LocalEmbeddingWorker
from src.back.worker.workers.sigmaref_discovery_worker import SigmaRefDiscoveryWorker
from src.back.worker.workers.sigmaref_embedding_worker import SigmaRefEmbeddingWorker

logger = logging.getLogger(__name__)


class TaskDispatcher:
    """Main engine that dispatches tasks to specialized workers."""

    def __init__(self, poll_interval: int = 5):
        self.poll_interval = poll_interval
        self.db = DatabaseService.get_instance()
        self._running = False
        self._workers: Dict[str, Type[BaseWorker]] = {
            "sigmaref_discovery": SigmaRefDiscoveryWorker,
            "github_discovery": GithubDiscoveryWorker,
            "local_discovery": LocalDiscoveryWorker,
            "sigmaref_embeddings": SigmaRefEmbeddingWorker,
            "github_embeddings": GithubEmbeddingWorker,
            "local_embeddings": LocalEmbeddingWorker,
        }

    async def run(self):
        """Main loop to monitor and dispatch tasks."""
        self._running = True
        self.db.reset_stale_embed_tasks()
        self.db.reset_stale_workers()
        logger.info("Task Dispatcher started with %d workers.", len(self._workers))

        while self._running:
            try:
                tasks = self.db.get_active_embed_tasks()

                for task in tasks:
                    if task["status"] == "pending":
                        await self._dispatch(task)
                    elif task["status"] == "running":
                        continue

            except Exception as e:
                logger.error(f"Dispatcher loop error: {e}", exc_info=True)

            await asyncio.sleep(self.poll_interval)

    async def _dispatch(self, task: dict):
        """Dispatches a single task to the appropriate worker using atomic claim."""
        task_id = task["task_id"]
        task_type = task.get("task_type", "embeddings")
        collection_name = task.get("collection_name", "")

        if not self.db.claim_task(task_id):
            logger.info(f"Task {task_id} already claimed by another dispatcher, skipping")
            return

        logger.info(f"Dispatching task {task_id} (type: {task_type})")

        self.db.upsert_worker_state(
            worker_type=task_type,
            status="running",
            current_task_id=task_id,
        )

        self.db.upsert_embed_progress(
            task_id=task_id,
            task_type=task_type,
            status="running",
            collection_name=collection_name,
        )

        worker_cls = self._workers.get(task_type)
        if not worker_cls:
            error_msg = f"No worker registered for task type: {task_type}"
            logger.error(f"Task {task_id} failed: {error_msg}")
            self.db.upsert_embed_progress(
                task_id=task_id,
                status="failed",
                errors=error_msg,
                collection_name=collection_name,
            )
            self.db.upsert_worker_state(
                worker_type=task_type,
                status="idle",
                current_task_id="",
                error=error_msg,
            )
            return

        worker = worker_cls(self.db)
        try:
            await worker.process(task)
            self.db.upsert_embed_progress(
                task_id=task_id,
                status="completed",
                collection_name=collection_name,
            )
        except Exception as e:
            logger.error(f"Worker execution failed for task {task_id}: {e}", exc_info=True)
            self.db.upsert_embed_progress(
                task_id=task_id,
                status="failed",
                errors=str(e),
                collection_name=collection_name,
            )
        finally:
            self.db.upsert_worker_state(
                worker_type=task_type,
                status="idle",
                current_task_id="",
                error="",
            )

    def stop(self):
        self._running = False
