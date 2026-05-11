"""Test RAG pipeline."""

import pytest
from src.back.rag.pipeline import RAGPipeline

@pytest.mark.asyncio
async def test_rag_pipeline_init() -> None:
    """Test RAG pipeline initialization."""
    pipeline = RAGPipeline()
    assert pipeline._initialized is False


@pytest.mark.asyncio
async def test_rag_pipeline_initialize() -> None:
    """Test RAG pipeline initialize."""
    pipeline = RAGPipeline()
    pipeline.initialize()
    assert pipeline._initialized is True


@pytest.mark.asyncio
async def test_rag_pipeline_search() -> None:
    """Test RAG pipeline search."""
    pipeline = RAGPipeline()
    results = await pipeline.search("test query")
    assert results == []


@pytest.mark.asyncio
async def test_rag_pipeline_index() -> None:
    """Test RAG pipeline index."""
    pipeline = RAGPipeline()
    await pipeline.index(
        embeddings=[[0.1, 0.2, 0.3]],
        documents=["test document"],
        metadata=[{"id": "1"}]
    )
