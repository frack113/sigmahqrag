import asyncio
import logging
from src.back.worker.base import BaseWorker

logger = logging.getLogger(__name__)

class EmbeddingWorker(BaseWorker):
    """Specialized worker for embedding tasks."""
    async def process(self, task: dict) -> None:
        task_id = task['task_id']
        collection_name = task['collection_name']
        logger.info(f"[EmbeddingWorker] Processing task {task_id}")
        
        # Placeholder for actual embedding logic (e.g. llama.cpp, Qdrant)
        await asyncio.sleep(2) 
        
        self.db.upsert_embed_progress(
            task_id=task_id,
            status='completed',
            progress_percent=100.0,
            collection_name=collection_name
        )
