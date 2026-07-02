"""Tests for RAG pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.application.chat.rag import RAGPipeline
from src.core.sigma.models import SigmaRule


@pytest.fixture
def rag_pipeline() -> RAGPipeline:
    """Create RAG pipeline with fully mocked dependencies."""
    with (
        patch("src.application.chat.rag.SearchEngine") as mock_search,
        patch("src.application.chat.rag.LlamaClient") as mock_llm,
    ):
        pipeline = RAGPipeline()
        pipeline.search_engine = mock_search.return_value
        pipeline.llm_client = mock_llm.return_value
        pipeline._resolve_prompt = MagicMock(return_value="You are a helpful assistant.")
        pipeline.env = MagicMock()
        yield pipeline


@pytest.fixture
def sigma_rule() -> SigmaRule:
    """Create a test SigmaRule."""
    return SigmaRule(
        id="test_001",
        title="Test Rule",
        description="A test rule",
        detection={"selection": {"EventID": 4625}},
    )


@pytest.mark.asyncio
async def test_explain_rule(rag_pipeline: RAGPipeline, sigma_rule: SigmaRule) -> None:
    """Test rule explanation with LLM."""
    rag_pipeline.llm_client.generate = AsyncMock(return_value="Rule explanation here")

    result = await rag_pipeline.explain_rule(sigma_rule)
    assert result == "Rule explanation here"
    rag_pipeline.llm_client.generate.assert_called_once()


@pytest.mark.asyncio
async def test_explain_rule_fallback(rag_pipeline: RAGPipeline) -> None:
    """Test fallback when LLM fails."""
    rule = SigmaRule(
        id="test_001",
        title="Test Rule",
        description="A test rule",
        detection={"selection": {"EventID": 4625}},
    )

    rag_pipeline.llm_client.generate = AsyncMock(side_effect=Exception("LLM down"))

    result = await rag_pipeline.explain_rule(rule)
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
    rule = SigmaRule(
        id="test_001",
        title="Test Rule",
        detection={"selection": {"EventID": 4625}},
    )
    results = [{"text": "Related rule", "citation": "sigma:related"}]

    rag_pipeline.llm_client.generate = AsyncMock(return_value="Coverage analysis here")

    result = await rag_pipeline.analyze_coverage(rule, results)
    assert result == "Coverage analysis here"
