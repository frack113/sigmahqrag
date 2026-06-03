from __future__ import annotations

import logging
from pathlib import Path

from llama_index.core.schema import Document
from llama_index.core.node_parser import SentenceSplitter

from ..base import DocumentTransform
from ..registry import TransformRegistry

logger = logging.getLogger(__name__)


class PDFTransform(DocumentTransform):
    """Parse PDF files into LlamaIndex Document objects."""

    FORMAT_NAME = "pdf"
    SUPPORTED_EXTENSIONS = (".pdf",)

    def parse(self, file_path: Path) -> list[Document]:
        from llama_index.readers.file import PyMuPDFReader

        reader = PyMuPDFReader()
        return reader.load_data(file_path)

    def chunk(self, documents: list[Document]) -> list[Document]:
        splitter = SentenceSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        return splitter(documents)  # type: ignore[return-value]


TransformRegistry.register(PDFTransform)
