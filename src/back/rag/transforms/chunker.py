"""Document chunker — delegates to IngestionPipeline's SentenceSplitter."""

from __future__ import annotations

from typing import Any

from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document

from src.back.rag.ingestion import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE


class Chunker:
    """Document chunker wrapping IngestionPipelineBuilder's SentenceSplitter."""

    def __init__(self, max_chunk_size: int = DEFAULT_CHUNK_SIZE) -> None:
        from src.back.rag.ingestion import IngestionPipelineBuilder

        self._builder = IngestionPipelineBuilder()
        self._splitter = SentenceSplitter(
            chunk_size=max_chunk_size,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP,
            include_metadata=True,
        )

    def chunk(self, document: dict[str, Any]) -> list[dict[str, Any]]:
        text = document.get("text")
        if not text:
            return []
        metadata = document.get("metadata") or {}
        doc = Document(text=text, metadata=metadata)
        nodes = self._splitter([doc])
        return [{"text": n.text, "metadata": n.metadata} for n in nodes]

    def chunk_documents(self, documents: list[Document]) -> list[dict[str, Any]]:
        nodes = self._splitter(documents)
        return [{"text": n.text, "metadata": n.metadata} for n in nodes]
