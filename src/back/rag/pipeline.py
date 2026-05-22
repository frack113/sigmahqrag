"""RAG pipeline implementation — delegates to IngestionPipelineBuilder."""

from __future__ import annotations

import logging
from typing import Any

from llama_index.core.schema import Document

from src.back.rag.ingestion import IngestionPipelineBuilder
from src.back.rag.search import SearchEngine

logger = logging.getLogger(__name__)


class RAGPipeline:
    """RAG pipeline for semantic search backed by IngestionPipelineBuilder."""

    def __init__(self) -> None:
        """Initialize the pipeline."""
        self.search_engine = SearchEngine()
        self._builder: IngestionPipelineBuilder | None = None

    @property
    def builder(self) -> IngestionPipelineBuilder:
        if self._builder is None:
            self._builder = IngestionPipelineBuilder()
        return self._builder

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for similar documents."""
        return await self.search_engine.search(query, top_k=limit)

    def index_documents(self, documents: list[Document], num_workers: int = 4) -> list[Any]:
        """Index documents via IngestionPipelineBuilder."""
        try:
            return self.builder.run(documents, num_workers=num_workers)
        except Exception as e:
            logger.exception("Failed to index documents: %s", e)
            raise

    def query_engine(self, similarity_top_k: int = 5):
        """Get a query engine from the ingestion pipeline."""
        return self.builder.as_query_engine(similarity_top_k=similarity_top_k)
