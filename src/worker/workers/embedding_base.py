import logging
from abc import abstractmethod
from pathlib import Path

from llama_index.core.node_parser import MarkdownNodeParser
from llama_index.core.schema import Document

from src.back.rag.ingestion import IngestionPipelineBuilder
from src.back.utils.identify_file_type import FileType
from src.worker.base import BaseWorker
from src.worker.enums import WorkerName, WorkerStatus

logger = logging.getLogger(__name__)

_OFFICE_TEXT_FORMATS = {".docx", ".doc", ".pptx", ".ppt", ".pptm"}
_OFFICE_SKIP_FORMATS = {".xlsx", ".xls", ".ods", ".odp", ".xlsm", ".xlsb"}


class EmbeddingWorker(BaseWorker):
    """Base class for embedding workers with shared progress tracking and error handling."""

    worker_type: WorkerName
    collection_name: str = ""

    def _parse_binary_document(self, file_path: Path, content_type: str) -> list[Document]:
        if content_type == FileType.PDF.value:
            from llama_index.readers.file import PyMuPDFReader

            return PyMuPDFReader().load_data(file_path)

        if content_type == FileType.OFFICE_DOCUMENT.value:
            ext = file_path.suffix.lower()
            if ext in _OFFICE_TEXT_FORMATS:
                if ext in (".docx", ".doc"):
                    from llama_index.readers.file import DocxReader

                    return DocxReader().load_data(file_path)
                if ext in (".pptx", ".ppt", ".pptm"):
                    from llama_index.readers.file import PptxReader

                    return PptxReader().load_data(file_path)
            raise ValueError(f"Unsupported office format: {ext}")

        raise ValueError(f"Unsupported binary format: {content_type}")

    def process(self, task: dict) -> None:
        assert self.dispatcher is not None
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

        self.dispatcher.update_worker_state(
            worker_type=self.worker_type,
            status=WorkerStatus.RUNNING,
            current_task_id=task_id,
            progress_percent=0.0,
        )

        builder = IngestionPipelineBuilder(collection_name=self._collection_name)
        valid_docs: list[tuple[Document, dict]] = []

        for idx, entry in enumerate(entries):
            file_path = self._resolve_file_path(entry)
            current_file = entry.get("file_name", "") or entry.get("hash", "")

            if not file_path or not file_path.exists():
                logger.warning(f"[{self.__class__.__name__}] File not found: {file_path}")
                skipped.append(current_file)
                self._update_status(entry, "error")
                self.dispatcher.update_worker_state(
                    worker_type=self.worker_type,
                    progress_percent=round(((idx + 1) / total) * 10, 2),
                    current_file=current_file,
                )
                continue

            metadata = self._build_metadata(entry, self._collection_name)
            content_type = metadata.get("content_type", "")
            source = metadata.get("source", "")

            _binary_types = {FileType.PDF.value, FileType.OFFICE_DOCUMENT.value}
            if content_type in _binary_types:
                ext = file_path.suffix.lower()
                if content_type == FileType.OFFICE_DOCUMENT.value and ext in _OFFICE_SKIP_FORMATS:
                    logger.warning(
                        f"[{self.__class__.__name__}] Skipping unsupported office format {ext}: "
                        f"{file_path}"
                    )
                    skipped.append(current_file)
                    self._update_status(entry, "skipped")
                    self.dispatcher.update_worker_state(
                        worker_type=self.worker_type,
                        progress_percent=round(((idx + 1) / total) * 10, 2),
                        current_file=current_file,
                    )
                    continue

                try:
                    reader_docs = self._parse_binary_document(file_path, content_type)
                except Exception as e:
                    logger.warning(
                        f"[{self.__class__.__name__}] Error parsing {content_type} {file_path}: {e}"
                    )
                    errors.append({"file": current_file, "error": str(e)})
                    self._update_status(entry, "error")
                    self.dispatcher.update_worker_state(
                        worker_type=self.worker_type,
                        progress_percent=round(((idx + 1) / total) * 10, 2),
                        current_file=current_file,
                    )
                    continue

                for doc in reader_docs:
                    merged_metadata = {**metadata, **doc.metadata}
                    doc.metadata = merged_metadata
                    valid_docs.append((doc, entry))

                self.dispatcher.update_worker_state(
                    worker_type=self.worker_type,
                    progress_percent=round(((idx + 1) / total) * 10, 2),
                    current_file=current_file,
                )
                continue

            try:
                doc_text = file_path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"[{self.__class__.__name__}] Error reading {file_path}: {e}")
                errors.append({"file": current_file, "error": str(e)})
                self._update_status(entry, "error")
                self.dispatcher.update_worker_state(
                    worker_type=self.worker_type,
                    progress_percent=round(((idx + 1) / total) * 10, 2),
                    current_file=current_file,
                )
                continue

            if source in ("sigmaref", "github", "local") and content_type in ("markdown", ""):
                md_parser = MarkdownNodeParser(include_metadata=True)
                doc = Document(text=doc_text, metadata=metadata)
                parsed_nodes = md_parser.get_nodes_from_documents([doc])
                for node in parsed_nodes:
                    enriched_metadata = {**metadata, **node.metadata}
                    valid_docs.append((Document(text=node.text, metadata=enriched_metadata), entry))
            else:
                valid_docs.append((Document(text=doc_text, metadata=metadata), entry))

            self.dispatcher.update_worker_state(
                worker_type=self.worker_type,
                progress_percent=round(((idx + 1) / total) * 10, 2),
                current_file=current_file,
            )

        if valid_docs:
            entry_to_docs: dict[int, tuple[dict, list[Document]]] = {}
            for doc, entry in valid_docs:
                eid = id(entry)
                if eid not in entry_to_docs:
                    entry_to_docs[eid] = (entry, [])
                entry_to_docs[eid][1].append(doc)

            entry_groups = list(entry_to_docs.values())
            embedded_count = 0
            batch_size = max(1, len(entry_groups) // 20 or 1)

            for i in range(0, len(entry_groups), batch_size):
                batch = entry_groups[i : i + batch_size]
                batch_docs = []
                for e, docs in batch:
                    batch_docs.extend(docs)

                try:
                    builder.run(documents=batch_docs)
                    for e, _ in batch:
                        self._update_status(e, "embedded")
                except Exception as e:
                    logger.error(f"[{self.__class__.__name__}] Error embedding batch: {e}")
                    for entry_obj, _ in batch:
                        self._update_status(entry_obj, "error")
                        errors.append(
                            {
                                "file": entry_obj.get("file_name", "") or entry_obj.get("hash", ""),
                                "error": str(e),
                            }
                        )

                embedded_count += len(batch)
                self.dispatcher.update_worker_state(
                    worker_type=self.worker_type,
                    progress_percent=round(10 + (embedded_count / total) * 90, 2),
                )

        self.dispatcher.update_worker_state(
            worker_type=self.worker_type,
            progress_percent=100.0,
        )

        processed = len(entry_to_docs) if valid_docs else 0
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
