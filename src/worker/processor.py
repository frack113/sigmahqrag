import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, Future
from typing import Dict, Type

from src.back.database.service import DatabaseService
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
    """Main engine that dispatches tasks to specialized workers using a ThreadPoolExecutor.

    The only public entry point for requesting work is ``ask_for_worker``.
    The dispatcher alone controls when a WAITING worker transitions to RUNNING.
    """

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
        self._lock = threading.Lock()
        self._pending_tasks: Dict[WorkerName, dict] = {}
        self._executor: ThreadPoolExecutor | None = None
        self._thread: threading.Thread | None = None
        self._db: DatabaseService | None = None
        self._workers: Dict[WorkerName, BaseWorker] = {}
        self._worker_states: Dict[WorkerName, dict] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def ask_for_worker(self, worker_type: WorkerName, **task_params) -> str | None:
        """Atomic check-and-set: if the worker is IDLE, mark it WAITING and store the task.

        Returns the generated ``task_id`` when the request was accepted, ``None`` when
        the worker is already WAITING, RUNNING, or in ERROR state.
        The dispatcher generates the task_id internally.
        """
        with self._lock:
            state = self._worker_states.get(worker_type)
            current_status = state["status"] if state else WorkerStatus.IDLE
            if current_status != WorkerStatus.IDLE:
                return None

            task_id = str(uuid.uuid4())
            self._worker_states[worker_type] = {
                "status": WorkerStatus.WAITING,
                "current_task_id": task_id,
                "error": "",
                "progress_percent": 0,
                "current_file": "",
            }
            self._pending_tasks[worker_type] = {"task_id": task_id, **task_params}
            logger.debug(f"Worker {worker_type.value} accepted task {task_id} (→ WAITING)")
            return task_id

    def get_all_worker_states(self) -> list[dict]:
        """Return all worker states as a list of dictionaries."""
        with self._lock:
            return [{"worker_type": k.value, **v} for k, v in self._worker_states.items()]

    def update_worker_state(self, worker_type: WorkerName, **kwargs):
        """Update the in-memory state for a specific worker type (called by workers)."""
        with self._lock:
            if worker_type not in self._worker_states:
                self._worker_states[worker_type] = {
                    "status": WorkerStatus.IDLE,
                    "current_task_id": "",
                    "error": "",
                    "progress_percent": 0,
                    "current_file": "",
                }
            self._worker_states[worker_type].update(kwargs)

    def get_worker_progress(self, worker_type: str) -> dict | None:
        """Return the current progress dict for a worker type, or None if unknown."""
        with self._lock:
            for wt, state in self._worker_states.items():
                if wt.value == worker_type:
                    return {
                        k: v.value if isinstance(v, WorkerStatus) else v
                        for k, v in state.items()
                        if k != "current_task_id"
                    }
            return None

    def is_worker_busy(self, worker_type: WorkerName) -> bool:
        """Return True if the worker is not IDLE."""
        with self._lock:
            state = self._worker_states.get(worker_type)
            if state is None:
                return False
            return state.get("status") != WorkerStatus.IDLE

    def get_progress_worker(self, worker_type: WorkerName) -> int:
        """Return progress percentage 0-100 for a worker type."""
        with self._lock:
            state = self._worker_states.get(worker_type)
            if state is None:
                return 0
            return state.get("progress_percent", 0)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self):
        """Start the dispatcher in a background thread using a ThreadPoolExecutor."""
        self._running = True

        self._db = DatabaseService.get_instance()

        self._workers = {name: cls(self._db, self) for name, cls in self._WORKER_TYPES.items()}
        for name in self._WORKER_TYPES:
            self._worker_states[name] = {
                "status": WorkerStatus.IDLE,
                "current_task_id": "",
                "error": "",
                "progress_percent": 0,
                "current_file": "",
            }
        logger.info("TaskDispatcher initialized with %d workers.", len(self._workers))

        self._executor = ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="WorkerExecutor",
        )

        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="TaskDispatcher")
        self._thread.start()
        logger.info("TaskDispatcher started (max_workers=%d).", self.max_workers)

    def stop(self, timeout: int = 30):
        """Signal the dispatcher to stop and shut down the executor."""
        self._running = False
        if self._executor:
            self._executor.shutdown(wait=True, cancel_futures=True)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("TaskDispatcher stopped.")

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    def _run_loop(self):
        """Poll for WAITING workers and submit them to the thread pool."""
        while self._running:
            launched = False
            with self._lock:
                waiting_workers = [
                    name
                    for name, state in self._worker_states.items()
                    if state.get("status") == WorkerStatus.WAITING
                ]
                for worker_type in waiting_workers:
                    task = self._pending_tasks.pop(worker_type, None)
                    if not task:
                        self._worker_states[worker_type]["status"] = WorkerStatus.IDLE
                        continue

                    worker = self._workers.get(worker_type)
                    if not worker:
                        error_msg = f"No worker registered for type: {worker_type.value}"
                        logger.error(error_msg)
                        self._worker_states[worker_type] = {
                            "status": WorkerStatus.IDLE,
                            "current_task_id": "",
                            "error": error_msg,
                            "progress_percent": 0,
                            "current_file": "",
                        }
                        continue

                    self._worker_states[worker_type]["status"] = WorkerStatus.RUNNING
                    logger.debug(
                        f"Submitting task {task.get('task_id', '')} (type: {worker_type.value}) → RUNNING"
                    )
                    try:
                        future: Future = self._executor.submit(
                            self._run_worker, worker_type, worker, task
                        )
                    except Exception as e:
                        logger.error(f"Failed to submit task for {worker_type.value}: {e}")
                        self._worker_states[worker_type] = {
                            "status": WorkerStatus.IDLE,
                            "current_task_id": "",
                            "error": str(e),
                            "progress_percent": 0,
                            "current_file": "",
                        }
                        continue
                    future.add_done_callback(self._on_task_done)
                    launched = True

            if not launched:
                time.sleep(self.poll_interval)

    def _run_worker(self, worker_type: WorkerName, worker: BaseWorker, task: dict) -> None:
        """Execute a worker's process method and manage state transitions."""
        task_id = task.get("task_id", "")
        error: str | None = None

        try:
            worker.process(task)
            logger.debug(f"Task {task_id} completed successfully")
        except Exception as e:
            logger.error(f"Worker execution failed for task {task_id}: {e}", exc_info=True)
            error = str(e)
            raise
        finally:
            with self._lock:
                self._worker_states[worker_type]["status"] = WorkerStatus.IDLE
                self._worker_states[worker_type]["current_task_id"] = ""
                self._worker_states[worker_type]["error"] = error or ""
                self._worker_states[worker_type]["progress_percent"] = 0
            if self._db is not None:
                self._db.persist()

    def _on_task_done(self, future: Future) -> None:
        """Callback executed when a future completes."""
        try:
            exc = future.exception()
            if exc:
                logger.error(f"Task raised an exception: {exc}")
        except Exception as e:
            logger.error(f"Error retrieving future result: {e}")
