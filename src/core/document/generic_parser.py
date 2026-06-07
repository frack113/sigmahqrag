from __future__ import annotations

import logging
from pathlib import Path

from llama_index.core.schema import Document
from llama_index.core.node_parser import SentenceSplitter

from ..base import DocumentTransform
from ..registry import TransformRegistry

logger = logging.getLogger(__name__)


class GenericTransform(DocumentTransform):
    """Catch-all transform for any file type not handled by a specific transform.

    Reads raw text and applies SentenceSplitter. Registered last so it only
    activates when no other transform matches.
    """

    FORMAT_NAME = "generic"
    SUPPORTED_EXTENSIONS: tuple[str, ...] = ()

    @classmethod
    def can_handle(cls, file_path: Path | str) -> bool:  # noqa: D102
        return True

    def parse(self, file_path: Path) -> list[Document]:
        text = file_path.read_text(encoding="utf-8", errors="replace")
        return [
            Document(
                text=text,
                metadata={
                    "source_file": str(file_path),
                    "doc_type": "generic",
                    "file_name": file_path.name,
                },
            )
        ]

    def _chunk(self, documents: list[Document]) -> list[Document]:
        splitter = SentenceSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        return splitter(documents)  # type: ignore[return-value]


TransformRegistry.register(GenericTransform)
