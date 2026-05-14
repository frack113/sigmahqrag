"""RAG pipeline components."""

from src.back.rag.chunker import SigmaChunker, chunk_sigma_rule
from src.back.rag.embeddings import EmbeddingGenerator, embed_documents
from src.back.rag.ingestion import IngestionPipelineBuilder, get_pipeline
from src.back.rag.search import (
    SearchEngine,
    format_search_result,
    get_citation,
    search,
)

__all__ = [
    "SigmaChunker",
    "chunk_sigma_rule",
    "EmbeddingGenerator",
    "embed_documents",
    "IngestionPipelineBuilder",
    "get_pipeline",
    "SearchEngine",
    "search",
    "format_search_result",
    "get_citation",
]
