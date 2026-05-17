import asyncio
import logging
from pathlib import Path
from src.back.database.service import DatabaseService

logger = logging.getLogger(__name__)

class EmbeddingWorker:
    def __init__(self, poll_interval: int = 5):
        self.poll_interval = poll_interval
        self.db = DatabaseService.get_instance()
        self._running = False

    async def run(self):
        """Main loop to monitor and process tasks."""
        self._running = True
        logger.info("Embedding Worker started.")
        
        while self._running:
            try:
                # 1. Reset stale tasks (those that were 'running' but didn't update)
                tasks = self.db.get_active_embed_tasks()
                if tasks:
                    self.db.reset_stale_embed_tasks()

                # 2. Fetch active/pending tasks
                tasks = self.db.get_active_embed_tasks()
                
                for task in tasks:
                    if task['status'] == 'pending':
                        await self._process_task(task)
                    elif task['status'] == 'running':
                        # Already being handled by another thread/task or the same loop
                        continue

            except Exception as e:
                logger.error(f"Worker loop error: {e}", exc_info=True)
            
            await asyncio.sleep(self.poll_interval)
    
    def _is_task_stale(self, task: dict) -> bool:
        """Check if a task is stale (running but no updates for > 5 minutes)."""
        from datetime import datetime, timezone
        
        updated_at = task.get('updated_at')
        if not updated_at:
            return False
        
        try:
            updated = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            return (now - updated).total_seconds() > 300
        except (ValueError, TypeError):
            return False

    async def _process_task(self, task: dict):
        """Handles the execution of a single embedding task."""
        task_id = task['task_id']
        source_type = task.get('source_type', 'unknown')
        collection_name = task['collection_name']
        
        logger.info(f"Starting task {task_id} ({source_type})")

        # Update status to 'running'
        self.db.upsert_embed_progress(
            task_id=task_id,
            status='running',
            collection_name=collection_name
        )

        try:
            from src.api.v1.qdrant import _run_embed_sigmaref
            
            # Determine registry path based on source_type
            if source_type == 'local':
                registry_path = Path(task_id)
            elif source_type in ('sigma_ref', 'sigmaref'):
                registry_path = Path("data/documents/sigmaref")
            else: # github or others
                registry_path = Path("data/documents/sigmaref")

            # We define a callback that the ingestion logic will call
            async def progress_callback(percent: float, current_file: str):
                self.db.upsert_embed_progress(
                    task_id=task_id,
                    status='running',
                    progress_percent=percent,
                    current_file=current_file,
                    collection_name=collection_name
                )

            # Run the actual ingestion
            await _run_embed_sigmaref(
                task_id=task_id, 
                registry_path=registry_path,
                collection_name=collection_name,
                progress_callback=progress_callback
            )

            self.db.upsert_embed_progress(
                task_id=task_id,
                status='completed',
                progress_percent=100.0,
                collection_name=collection_name
            )

        except Exception as e:
            logger.error(f"Task failed for {task_id}: {e}", exc_info=True)
            self.db.upsert_embed_progress(
                task_id=task_id,
                status='failed',
                errors=str(e),
                collection_name=collection_name
            )

    def stop(self):
        self._running = False
