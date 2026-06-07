"""Tests for RAG pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.back.services.rag_pipeline import RAGPipeline


@pytest.fixture
def rag_pipeline() -> RAGPipeline:
    """Create RAG pipeline with fully mocked dependencies."""
    with (
        patch("src.back.services.rag_pipeline.SearchEngine") as mock_search,
        patch("src.back.services.rag_pipeline.LlamaClient") as mock_llm,
    ):
        pipeline = RAGPipeline()
        pipeline.search_engine = mock_search.return_value
        pipeline.llm_client = mock_llm.return_value
        # Mock _resolve_prompt to avoid DB access
        pipeline._resolve_prompt = MagicMock(return_value="You are a helpful assistant.")
        # Mock the jinja2 environment to avoid template loading
        pipeline.env = MagicMock()
        yield pipeline


@pytest.mark.asyncio
async def test_explain_rule(rag_pipeline: RAGPipeline) -> None:
    """Test rule explanation with LLM."""
    rule_data = {
        "id": "test_001",
        "name": "Test Rule",
        "description": "A test rule",
        "detection": {"selection": {"EventID": 4625}},
    }

    rag_pipeline.llm_client.generate = AsyncMock(return_value="Rule explanation here")

    result = await rag_pipeline.explain_rule(rule_data)
    assert result == "Rule explanation here"
    rag_pipeline.llm_client.generate.assert_called_once()


@pytest.mark.asyncio
async def test_explain_rule_fallback(rag_pipeline: RAGPipeline) -> None:
    """Test fallback when LLM fails."""
    rule_data = {
        "id": "test_001",
        "name": "Test Rule",
        "description": "A test rule",
    }

    rag_pipeline.llm_client.generate = AsyncMock(side_effect=Exception("LLM down"))

    result = await rag_pipeline.explain_rule(rule_data)
    assert "**Rule:** Test Rule" in result


@pytest.mark.asyncio
async def test_answer_search_query(rag_pipeline: RAGPipeline) -> None:
    """Test search query answering."""
    results = [
        {"text": "Rule 1 content", "citation": "sigma:rule1"},
        {"text": "Rule 2 content", "citation": "sigma:rule2"},
    ]

    rag_pipeline.llm_client.generate = AsyncMock(return_value="Search answer here")

    result = await rag_pipeline.answer_search_query("What about EventID?", results)
    assert result == "Search answer here"
    rag_pipeline.llm_client.generate.assert_called_once()


@pytest.mark.asyncio
async def test_analyze_coverage(rag_pipeline: RAGPipeline) -> None:
    """Test coverage analysis."""
    rule_data = {"id": "test_001", "name": "Test Rule"}
    results = [{"text": "Related rule", "citation": "sigma:related"}]

    rag_pipeline.llm_client.generate = AsyncMock(return_value="Coverage analysis here")

    result = await rag_pipeline.analyze_coverage(rule_data, results)
    assert result == "Coverage analysis here"
