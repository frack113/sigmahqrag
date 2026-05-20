import asyncio
import logging
from abc import abstractmethod
from pathlib import Path

from llama_index.core.schema import Document

from src.back.rag.ingestion import IngestionPipelineBuilder
from src.worker.base import BaseWorker

logger = logging.getLogger(__name__)


class EmbeddingWorker(BaseWorker):
    """Base class for embedding workers with shared progress tracking and error handling."""

    worker_type: str = ""
    collection_name: str = ""

    async def process(self, task: dict) -> None:
        task_id = task.get("task_id", "")
        self._collection_name = task.get("collection_name", self.collection_name)
        self._task = task

        entries = self._get_entries(task)
        if not entries:
            logger.debug(f"[{self.__class__.__name__}] No entries to embed")
            return

        total = len(entries)
        errors: list[dict] = []
        skipped: list[str] = []

        self.db.upsert_worker_state(
            worker_type=self.worker_type,
            status="running",
            current_task_id=task_id,
            progress_percent=0.0,
        )

        builder = IngestionPipelineBuilder(collection_name=self._collection_name)

        for idx, entry in enumerate(entries):
            file_path = self._resolve_file_path(entry)
            current_file = entry.get("file_name", "") or entry.get("hash", "")

            if not file_path or not file_path.exists():
                logger.warning(f"[{self.__class__.__name__}] File not found: {file_path}")
                skipped.append(current_file)
                self._update_status(entry, "error")
                continue

            try:
                doc_text = file_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"[{self.__class__.__name__}] Error reading {file_path}: {e}")
                errors.append({"file": current_file, "error": str(e)})
                self._update_status(entry, "error")
                continue

            metadata = self._build_metadata(entry, self._collection_name)
            doc = Document(text=doc_text, metadata=metadata)

            try:
                builder.run(documents=[doc])
                self._update_status(entry, "embedded")
            except Exception as e:
                logger.error(f"[{self.__class__.__name__}] Error embedding {current_file}: {e}")
                errors.append({"file": current_file, "error": str(e)})
                self._update_status(entry, "error")

            processed = idx + 1 - len(errors) - len(skipped)
            progress = (processed / total) * 100 if total > 0 else 0
            self.db.update_worker_progress(
                worker_type=self.worker_type,
                progress_percent=round(progress, 2),
                current_file=current_file,
            )

            await asyncio.sleep(0)

        processed = total - len(errors) - len(skipped)
        self.db.update_worker_progress(
            worker_type=self.worker_type,
            progress_percent=100.0,
        )

        logger.info(
            f"[{self.__class__.__name__}] Complete: {processed}/{total} embedded, "
            f"{len(errors)} errors, {len(skipped)} skipped"
        )

    @abstractmethod
    def _get_entries(self, task: dict) -> list[dict]:
        """Return list of entries to embed."""
        ...

    @abstractmethod
    def _resolve_file_path(self, entry: dict) -> Path | None:
        """Resolve the file path for an entry."""
        ...

    @abstractmethod
    def _build_metadata(self, entry: dict, collection_name: str) -> dict:
        """Build metadata dict for the document."""
        ...

    @abstractmethod
    def _update_status(self, entry: dict, status: str) -> None:
        """Update the embedding status for an entry."""
        ...
