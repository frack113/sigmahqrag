"""RAG pipeline implementation — delegates to IngestionPipelineBuilder."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class RAGPipeline:
    """RAG pipeline for semantic search backed by IngestionPipelineBuilder."""

    def __init__(self) -> None:
        """Initialize the pipeline."""
        from src.core.search.engine import SearchEngine

        self.search_engine = SearchEngine()

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search for similar documents."""
        return await self.search_engine.search(query, top_k=limit)
