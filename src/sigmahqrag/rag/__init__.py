"""RAG pipeline components."""

from sigmahqrag.rag.chunker import SigmaChunker, chunk_sigma_rule
from sigmahqrag.rag.embeddings import EmbeddingGenerator, embed_documents
from sigmahqrag.rag.search import (
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
    "SearchEngine",
    "search",
    "format_search_result",
    "get_citation",
]
