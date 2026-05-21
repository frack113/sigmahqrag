import logging
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, Future
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

from src.worker.enums import WorkerStatus, WorkerName

logger = logging.getLogger(__name__)

class TaskDispatcher:
    """Main engine that dispatches tasks to specialized workers using a ThreadPoolExecutor."""

    _WORKER_TYPES: Dict[WorkerName, Type[BaseWorker]] = {
        WorkerName.SIGMAREF_DISCOVERY: SigmaRefDiscoveryWorker,
        WorkerName.GITHUB_DISCOVERY: GithubDiscoveryWorker,
        WorkerName.LOCAL_DISCOVERY: LocalDiscoveryWorker,
        WorkerName.SIGMAREF_EMBEDDINGS: SigmaRefEmbeddingWorker,
        WorkerName.GITHUB_EMBEDDINGS: GithubEmbeddingWorker,
        WorkerName.LOCAL_EMBEDDINGS: LocalEmbeddingWorker,
        WorkerName.MODEL_SYNC: ModelSyncWorker,
    }

    def __init__(self, poll_interval: float = 1.0, max_workers: int = 1):
        self.poll_interval = poll_interval
        self.max_workers = max_workers
        self._running = False
        self._task_queue: queue.Queue[tuple[str, dict]] = queue.Queue()
        self._executor: ThreadPoolExecutor | None = None
        self._thread: threading.Thread | None = None
        self._db: BufferedDatabaseService | None = None
        self._workers: Dict[WorkerName, BaseWorker] = {}
        self._worker_states: Dict[WorkerName, dict] = {}

    def update_worker_state(self, worker_type: WorkerName, **kwargs):
        """Update the in-memory state for a specific worker type."""
        if worker_type not in self._worker_states:
            self._worker_states[worker_type] = {
                "status": WorkerStatus.IDLE,
                "current_task_id": "",
                "error": "",
                "progress_percent": 0,
                "current_file": ""
            }
        self._worker_states[worker_type].update(kwargs)

    def get_all_worker_states(self) -> list[dict]:
        """Return all worker states as a list of dictionaries."""
        return [{"worker_type": k, **v} for k, v in self._worker_states.items()]

    def is_worker_busy(self, worker_type: WorkerName) -> bool:
        """Check if a specific worker is currently busy/running."""
        state = self._worker_states.get(worker_type, {})
        return state.get("status") == WorkerStatus.RUNNING

    def start(self):
        """Start the dispatcher in a background thread using a ThreadPoolExecutor."""
        self._running = True

        base_db = DatabaseService.get_instance()
        journal_path = Path("data/worker_journal.log")
        self._db = BufferedDatabaseService(base_db, journal_path)

        self._workers = {name: cls(self._db, self) for name, cls in self._WORKER_TYPES.items()}
        logger.info("TaskDispatcher initialized with %d workers.", len(self._workers))

        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="WorkerExecutor",
        )

        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="TaskDispatcher")
        self._thread.start()
        logger.info("TaskDispatcher started (max_workers=%d).", self.max_workers)

    def _run_loop(self):
        """Poll the task queue and submit work to the ThreadPoolExecutor."""
        while self._running:
            try:
                worker_type, task = self._task_queue.get(timeout=self.poll_interval)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Dispatcher loop error: {e}", exc_info=True)
                continue

            worker = self._workers.get(worker_type)
            if not worker:
                error_msg = f"No worker registered for task type: {worker_type.value}"
                logger.error(error_msg)
                self.update_worker_state(
                    worker_type=worker_type,
                    status=WorkerStatus.IDLE,
                    current_task_id="",
                    error=error_msg,
                )
                continue

            logger.debug(f"Submitting task {task.get('task_id', '')} (type: {worker_type.value})")
            future: Future = self._executor.submit(self._run_worker, worker_type, worker, task)

            future.add_done_callback(self._on_task_done)

    def _run_worker(self, worker_type: WorkerName, worker: BaseWorker, task: dict) -> None:
        """Execute a worker's process method and manage state transitions."""
        task_id = task.get("task_id", "")

        self.update_worker_state(
            worker_type=worker_type,
            status=WorkerStatus.RUNNING,
            current_task_id=task_id,
        )

        try:
            worker.process(task)
            logger.debug(f"Task {task_id} completed successfully")
        except Exception as e:
            logger.error(f"Worker execution failed for task {task_id}: {e}", exc_info=True)
            self.update_worker_state(
                worker_type=worker_type,
                status=WorkerStatus.IDLE,
                current_task_id="",
                error=str(e),
            )
            raise

    def _on_task_done(self, future: Future) -> None:
        """Callback executed when a future completes. Ensures DB flush."""
        try:
            exc = future.exception()
            if exc:
                logger.error(f"Task raised an exception: {exc}")
        except Exception as e:
            logger.error(f"Error retrieving future result: {e}")
        finally:
            try:
                self._db.flush()
            except Exception as e:
                logger.error(f"Failed to flush database after task: {e}")

    def queue_task(self, worker_type: WorkerName, task: dict) -> None:
        """Queue a task for execution (thread-safe, non-blocking)."""
        self._task_queue.put((worker_type, task))
        logger.debug(f"Queued task for {worker_type.value}")

    def stop(self, timeout: int = 30):
        """Signal the dispatcher to stop and shut down the executor."""
        self._running = False
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=True)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        if self._db:
            try:
                self._db.flush()
            except Exception as e:
                logger.error(f"Failed to flush database during shutdown: {e}")
        logger.info("TaskDispatcher stopped.")
