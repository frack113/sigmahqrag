"""Integration tests for complete chat flows."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from src.back.services.chat_service import ChatService


@pytest.fixture
def chat_service() -> ChatService:
    """Create ChatService with mocked dependencies."""
    # Create service first
    service = ChatService()

    # Mock search_engine
    service.search_engine = MagicMock()
    service.search_engine.search = AsyncMock(return_value=[])

    # Mock the rag_pipeline
    service.rag_pipeline = MagicMock()
    service.rag_pipeline.explain_rule = AsyncMock(
        return_value="This rule detects failed login attempts..."
    )
    service.rag_pipeline.answer_search_query = AsyncMock(return_value="I found 2 relevant rules...")
    service.rag_pipeline.analyze_coverage = AsyncMock(return_value="Coverage analysis: ...")
    service.rag_pipeline.cache = MagicMock()
    service.rag_pipeline.cache.invalidate = MagicMock()

    # Mock the validator
    service.validator = MagicMock()
    service.validator.validate.return_value = {
        "id": "test_001",
        "name": "Test Rule",
        "description": "A test rule",
        "detection": {"selection": {"EventID": 4625}},
    }

    # Mock the tool execution to avoid HTTP calls to LLM
    service._execute_tool_calls = AsyncMock(return_value="I found 2 relevant rules...")

    return service


@pytest.mark.asyncio
async def test_upload_then_explain_flow(chat_service: ChatService) -> None:
    """Test complete flow: upload YAML → explain rule."""
    # Upload a valid Sigma rule
    yaml_content = b"""
id: test_001
name: Test Rule
description: A test rule
detection:
    selection:
        EventID: 4625
"""
    rule_data = await chat_service.validate_and_store_yaml(yaml_content)
    assert rule_data["id"] == "test_001"

    # Explain the rule
    response = await chat_service._handle_explain("explain this rule")
    assert "detects failed login" in response.lower()
    chat_service.rag_pipeline.explain_rule.assert_called_once()


@pytest.mark.asyncio
async def test_search_flow(chat_service: ChatService) -> None:
    """Test search mode flow with LLM response."""
    # Mock search results
    chat_service.search_engine.search = AsyncMock(
        return_value=[
            {"text": "Rule 1 content", "citation": "sigma:rule_1", "score": 0.95},
            {"text": "Rule 2 content", "citation": "sigma:rule_2", "score": 0.85},
        ]
    )

    # Mock RAG pipeline response
    chat_service.rag_pipeline.answer_search_query = AsyncMock(
        return_value="I found 2 relevant rules..."
    )

    response = await chat_service._handle_search("failed logon events")
    assert "found" in response.lower()
    chat_service._execute_tool_calls.assert_called_once()


@pytest.mark.asyncio
async def test_coverage_flow(chat_service: ChatService) -> None:
    """Test coverage analysis flow."""
    # Setup uploaded rule
    chat_service._uploaded_rule = {
        "id": "test_001",
        "name": "Test Rule",
        "detection": {"selection": {"EventID": 4625}},
    }

    # Mock search results
    chat_service.search_engine.search = AsyncMock(
        return_value=[
            {"text": "Related rule 1", "citation": "sigma:rule_2"},
        ]
    )

    # Mock RAG pipeline response
    chat_service.rag_pipeline.analyze_coverage = AsyncMock(return_value="Coverage analysis: ...")

    response = await chat_service._handle_coverage("check coverage")
    assert "coverage" in response.lower()
    chat_service.rag_pipeline.analyze_coverage.assert_called_once()


@pytest.mark.asyncio
async def test_cache_invalidation_on_upload(chat_service: ChatService) -> None:
    """Test that cache is invalidated when new rule is uploaded."""
    yaml_content = b"""
id: test_002
name: New Rule
description: Another test
detection:
    selection:
        EventID: 4648
"""
    await chat_service.validate_and_store_yaml(yaml_content)
    chat_service.rag_pipeline.cache.invalidate.assert_called_once()


@pytest.mark.asyncio
async def test_fallback_when_llm_unavailable(chat_service: ChatService) -> None:
    """Test fallback responses when LLM fails."""
    # Mock RAG pipeline to raise exception
    chat_service.rag_pipeline.answer_search_query = AsyncMock(side_effect=Exception("LLM down"))

    # Mock search results
    chat_service.search_engine.search = AsyncMock(
        return_value=[
            {"text": "Some rule content", "score": 0.9},
        ]
    )

    response = await chat_service._handle_search("test query")
    # Should return fallback (not exception)
    assert response != ""
    assert "Some rule content" in response or "rule" in response.lower()
