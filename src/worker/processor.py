import asyncio
import logging
import threading
from typing import Dict, Type

from src.back.database.service import DatabaseService
from src.back.database import BufferedDatabaseService
from pathlib import Path
from src.worker.base import BaseWorker
from src.worker.workers.github_discovery_worker import GithubDiscoveryWorker
from src.worker.workers.github_embedding_worker import GithubEmbeddingWorker
from src.worker.workers.local_discovery_worker import LocalDiscoveryWorker
from src.worker.workers.local_embedding_worker import LocalEmbeddingWorker
from src.worker.workers.model_sync_worker import ModelSyncWorker
from src.worker.workers.sigmaref_discovery_worker import SigmaRefDiscoveryWorker
from src.worker.workers.sigmaref_embedding_worker import SigmaRefEmbeddingWorker

logger = logging.getLogger(__name__)


class TaskDispatcher:
    """Main engine that dispatches tasks to specialized workers in a background thread."""

    _WORKER_TYPES: Dict[str, Type[BaseWorker]] = {
        "sigmaref_discovery": SigmaRefDiscoveryWorker,
        "github_discovery": GithubDiscoveryWorker,
        "local_discovery": LocalDiscoveryWorker,
        "sigmaref_embeddings": SigmaRefEmbeddingWorker,
        "github_embeddings": GithubEmbeddingWorker,
        "local_embeddings": LocalEmbeddingWorker,
        "model_sync": ModelSyncWorker,
    }

    def __init__(self, poll_interval: int = 5):
        self.poll_interval = poll_interval
        self._running = False
        self._task_queue: asyncio.Queue[tuple[str, dict]] = asyncio.Queue()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self):
        """Start the dispatcher in a background thread with its own event loop."""
        self._running = True
        self._thread = threading.Thread(target=self._run_thread, daemon=True, name="TaskDispatcher")
        self._thread.start()
        logger.info("TaskDispatcher thread started.")

    def _run_thread(self):
        """Run the dispatcher loop in a dedicated thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        base_db = DatabaseService.get_instance()
        journal_path = Path("data/worker_journal.log")
        db = BufferedDatabaseService(base_db, journal_path)

        db.reset_stale_workers()

        workers: Dict[str, BaseWorker] = {name: cls(db) for name, cls in self._WORKER_TYPES.items()}
        logger.info("TaskDispatcher thread running with %d workers.", len(workers))

        async def dispatch(worker_type: str, task: dict):
            task_id = task.get("task_id", "")
            logger.debug(f"Dispatching task {task_id} (type: {worker_type})")

            worker = workers.get(worker_type)
            if not worker:
                error_msg = f"No worker registered for task type: {worker_type}"
                logger.error(f"Task {task_id} failed: {error_msg}")
                db.upsert_worker_state(
                    worker_type=worker_type,
                    status="idle",
                    current_task_id="",
                    error=error_msg,
                )
                return

            db.upsert_worker_state(
                worker_type=worker_type,
                status="running",
                current_task_id=task_id,
            )

            error_msg = ""
            try:
                await worker.process(task)
                logger.debug(f"Task {task_id} completed successfully")
            except Exception as e:
                error_msg = str(e)
                logger.error(f"Worker execution failed for task {task_id}: {e}", exc_info=True)
            finally:
                db.upsert_worker_state(
                    worker_type=worker_type,
                    status="idle",
                    current_task_id="",
                    error=error_msg,
                )

        async def main():
            iteration = 0
            while self._running:
                try:
                    iteration += 1
                    if iteration % 60 == 0:
                        db.reset_stale_workers()
                        db.flush()

                    try:
                        worker_type, task = self._task_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        await asyncio.sleep(1.0)
                        continue

                    await dispatch(worker_type, task)
                    self._task_queue.task_done()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Dispatcher thread error: {e}", exc_info=True)

        try:
            self._loop.run_until_complete(main())
        except Exception as e:
            logger.error(f"Dispatcher thread crashed: {e}", exc_info=True)
        finally:
            try:
                db.flush()
            except Exception as e:
                logger.error("Failed to flush database during shutdown: %s", e)
            self._loop.close()
            logger.info("TaskDispatcher thread stopped.")

    async def queue_task(self, worker_type: str, task: dict):
        """Queue a task for execution (thread-safe)."""
        await self._task_queue.put((worker_type, task))
        logger.debug(f"Queued task for {worker_type}")

    def stop(self):
        """Signal the dispatcher thread to stop."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
