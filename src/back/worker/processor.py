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

    _WORKER_TYPES: Dict[str, Type[BaseWorker]] = {
        "sigmaref_discovery": SigmaRefDiscoveryWorker,
        "github_discovery": GithubDiscoveryWorker,
        "local_discovery": LocalDiscoveryWorker,
        "sigmaref_embeddings": SigmaRefEmbeddingWorker,
        "github_embeddings": GithubEmbeddingWorker,
        "local_embeddings": LocalEmbeddingWorker,
    }

    def __init__(self, poll_interval: int = 5):
        self.poll_interval = poll_interval
        self.db = DatabaseService.get_instance()
        self._running = False
        self._workers = dict(self._WORKER_TYPES)
        self._pending_tasks: Dict[str, dict] = {}

    async def run(self):
        """Main loop to monitor and dispatch tasks."""
        self._running = True
        self.db.reset_stale_workers()
        logger.info("Task Dispatcher started with %d workers.", len(self._workers))

        while self._running:
            try:
                for worker_type, task in list(self._pending_tasks.items()):
                    if self.db.is_worker_busy(worker_type):
                        continue
                    
                    await self._dispatch(worker_type, task)

            except Exception as e:
                logger.error(f"Dispatcher loop error: {e}", exc_info=True)

            await asyncio.sleep(self.poll_interval)

    async def queue_task(self, worker_type: str, task: dict):
        """Queue a task for execution."""
        self._pending_tasks[worker_type] = task
        logger.info(f"Queued task for {worker_type}")

    async def _dispatch(self, worker_type: str, task: dict):
        """Dispatches a single task to the appropriate worker."""
        task_id = task.get("task_id", "")

        logger.info(f"Dispatching task {task_id} (type: {worker_type})")

        self.db.upsert_worker_state(
            worker_type=worker_type,
            status="running",
            current_task_id=task_id,
        )

        worker_cls = self._workers.get(worker_type)
        if not worker_cls:
            error_msg = f"No worker registered for task type: {worker_type}"
            logger.error(f"Task {task_id} failed: {error_msg}")
            self.db.upsert_worker_state(
                worker_type=worker_type,
                status="idle",
                current_task_id="",
                error=error_msg,
            )
            return

        worker = worker_cls(self.db)
        try:
            await worker.process(task)
            logger.info(f"Task {task_id} completed successfully")
        except Exception as e:
            logger.error(f"Worker execution failed for task {task_id}: {e}", exc_info=True)
            self.db.upsert_worker_state(
                worker_type=worker_type,
                status="idle",
                current_task_id="",
                error=str(e),
            )
        finally:
            self.db.upsert_worker_state(
                worker_type=worker_type,
                status="idle",
                current_task_id="",
                error="",
            )
            self._pending_tasks.pop(worker_type, None)

    def stop(self):
        self._running = False
