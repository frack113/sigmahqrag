from __future__ import annotations

import logging
from pathlib import Path

from llama_index.core.schema import Document
from llama_index.core.node_parser import SentenceSplitter

from ..base import DocumentTransform
from ..registry import TransformRegistry

logger = logging.getLogger(__name__)


class OfficeTransform(DocumentTransform):
    """Parse Office documents (DOCX, PPTX) into LlamaIndex Document objects."""

    FORMAT_NAME = "office"
    SUPPORTED_EXTENSIONS = (".docx", ".doc", ".pptx", ".ppt", ".pptm")

    def parse(self, file_path: Path) -> list[Document]:
        ext = file_path.suffix.lower()
        if ext in (".docx", ".doc"):
            from llama_index.readers.file import DocxReader

            docs = DocxReader().load_data(file_path)
        elif ext in (".pptx", ".ppt", ".pptm"):
            from llama_index.readers.file import PptxReader

            docs = PptxReader().load_data(file_path)
        else:
            logger.warning("Unsupported office format: %s", ext)
            return []
        for doc in docs:
            doc.metadata["doc_type"] = "office"
            doc.metadata["file_name"] = file_path.name
        return docs

    def _chunk(self, documents: list[Document]) -> list[Document]:
        splitter = SentenceSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        return splitter(documents)  # type: ignore[return-value]


TransformRegistry.register(OfficeTransform)
