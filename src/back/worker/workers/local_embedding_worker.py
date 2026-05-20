import asyncio
import logging
from pathlib import Path

from llama_index.core.schema import Document

from src.back.worker.base import BaseWorker
from src.back.rag.ingestion import IngestionPipelineBuilder

logger = logging.getLogger(__name__)


class LocalEmbeddingWorker(BaseWorker):
    """Embeds documents from a local directory into Qdrant.

    TODO: Complete implementation for next branch.
    - Support configurable base_path via task params
    - Handle missing files gracefully
    - Support incremental embedding (skip already embedded)
    """

    async def process(self, task: dict) -> None:
        collection_name = task.get("collection_name", "local")
        task_id = task.get("task_id", "")
        base_path = Path(task.get("base_path", "data/documents/local"))

        logger.info(f"[LocalEmbeddingWorker] Embedding local docs from {base_path} (WIP)")

        if not base_path.exists():
            logger.warning(f"[LocalEmbeddingWorker] Path does not exist: {base_path}")
            return

        registry_entries = self._get_registry_entries(collection_name)
        if not registry_entries:
            logger.info(f"[LocalEmbeddingWorker] No entries for {collection_name}")
            return

        total = len(registry_entries)
        errors = []
        skipped = []

        self.db.upsert_worker_state(
            worker_type="local_embeddings",
            status="running",
            current_task_id=task_id,
            progress_percent=0.0,
        )

        builder = IngestionPipelineBuilder(collection_name=collection_name)

        for idx, entry in enumerate(registry_entries):
            file_name = entry.get("file_name", "")
            file_path = base_path / file_name

            if not file_path.exists():
                logger.warning(f"[LocalEmbeddingWorker] File not found: {file_path}")
                skipped.append(file_name)
                continue

            try:
                doc_text = file_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"[LocalEmbeddingWorker] Error reading {file_path}: {e}")
                errors.append({"file": file_name, "error": str(e)})
                continue

            metadata = {
                "source": "local",
                "collection": collection_name,
                "file_name": file_name,
                "content_type": entry.get("content_type", ""),
            }

            doc = Document(text=doc_text, metadata=metadata)
            try:
                builder.run(documents=[doc])
            except Exception as e:
                logger.error(f"[LocalEmbeddingWorker] Error embedding {file_name}: {e}")
                errors.append({"file": file_name, "error": str(e)})

            processed = idx + 1 - len(errors) - len(skipped)
            progress = (processed / total) * 100 if total > 0 else 0
            self.db.update_worker_progress(
                worker_type="local_embeddings",
                progress_percent=round(progress, 2),
                current_file=file_name,
            )

            await asyncio.sleep(0)

        processed = total - len(errors) - len(skipped)
        self.db.update_worker_progress(
            worker_type="local_embeddings",
            progress_percent=100.0,
        )

        logger.info(
            f"[LocalEmbeddingWorker] Complete: {processed}/{total} embedded, "
            f"{len(errors)} errors, {len(skipped)} skipped"
        )

    def _get_registry_entries(self, collection_name: str) -> list[dict]:
        """Get doc_sigma_ref entries for local documents."""
        all_entries = self.db.get_doc_sigma_ref(limit=10000)
        return [
            e
            for e in all_entries
            if e.get("org") == "local"
            and e.get("repo") == collection_name
            and e.get("embed_status") == "discovery"
        ]
