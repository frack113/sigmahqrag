import asyncio
import logging
from typing import Dict, Type

from src.back.database.service import DatabaseService
from src.back.worker.base import BaseWorker
from src.back.worker.workers.discovery_worker import FileDiscoveryWorker
from src.back.worker.workers.embedding_worker import EmbeddingWorker

logger = logging.getLogger(__name__)

class TaskDispatcher:
    """Main engine that dispatches tasks to specialized workers."""
    def __init__(self, poll_interval: int = 5):
        self.poll_interval = poll_interval
        self.db = DatabaseService.get_instance()
        self._running = False
        self._workers: Dict[str, Type[BaseWorker]] = {
            'file_discovery': FileDiscoveryWorker,
            'embeddings': EmbeddingWorker
        }

    async def run(self):
        """Main loop to monitor and dispatch tasks."""
        self._running = True
        logger.info("Task Dispatcher started.")
        
        while self._running:
            try:
                # 1. Reset stale tasks
                self.db.reset_stale_embed_tasks()
                
                # 2. Fetch active/pending tasks
                tasks = self.db.get_active_embed_tasks()
                
                for task in tasks:
                    if task['status'] == 'pending':
                        await self._dispatch(task)
                    elif task['status'] == 'running':
                        continue

            except Exception as e:
                logger.error(f"Dispatcher loop error: {e}", exc_info=True)
            
            await asyncio.sleep(self.poll_interval)

    async def _dispatch(self, task: dict):
        """Dispatches a single task to the appropriate worker."""
        task_id = task['task_id']
        task_type = task.get('task_type', 'embeddings')
        collection_name = task['collection_name']

        logger.info(f"Dispatching task {task_id} (type: {task_type})")

        # Update status to 'running'
        self.db.upsert_embed_progress(
            task_id=task_id,
            task_type=task_type,
            status='running',
            collection_name=collection_name
        )

        worker_cls = self._workers.get(task_type)
        if not worker_cls:
            error_msg = f"No worker registered for task type: {task_type}"
            logger.error(f"Task {task_id} failed: {error_msg}")
            self.db.upsert_embed_progress(
                task_id=task_id,
                status='failed',
                errors=error_msg,
                collection_name=collection_name
            )
            return

        worker = worker_cls(self.db)
        try:
            await worker.process(task)
        except Exception as e:
            logger.error(f"Worker execution failed for task {task_id}: {e}", exc_info=True)
            self.db.upsert_embed_progress(
                task_id=task_id,
                status='failed',
                errors=str(e),
                collection_name=collection_name
            )

    def stop(self):
        self._running = False

# For backward compatibility with the existing startup logic (main.py uses EmbeddingWorker class name)
class EmbeddingWorker(TaskDispatcher):
    """Backward compatible wrapper for TaskDispatcher."""
    async def run(self):
        await super().run()
