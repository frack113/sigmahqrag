"""Integration tests for complete chat flows."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from src.application.chat.service import ChatService
from src.core.sigma.models import SigmaRule


def _make_test_rule(**overrides: str) -> SigmaRule:
    data = {
        "id": "test_001",
        "title": "Test Rule",
        "description": "A test rule",
        "detection": {"selection": {"EventID": 4625}},
        "logsource": {"category": "process_creation", "product": "windows"},
        **overrides,
    }
    return SigmaRule(**data)


@pytest.fixture
def chat_service() -> ChatService:
    """Create ChatService with mocked dependencies."""
    service = ChatService()

    service.search_engine = MagicMock()
    service.search_engine.search = AsyncMock(return_value=[])

    service.rag_pipeline = MagicMock()
    service.rag_pipeline.explain_rule = AsyncMock(
        return_value="This rule detects failed login attempts..."
    )
    service.rag_pipeline.answer_search_query = AsyncMock(return_value="I found 2 relevant rules...")
    service.rag_pipeline.analyze_coverage = AsyncMock(return_value="Coverage analysis: ...")
    service.rag_pipeline.cache = MagicMock()
    service.rag_pipeline.cache.invalidate = MagicMock()

    service.validator = MagicMock()
    service.validator.validate.return_value = _make_test_rule()

    service._execute_tool_calls = AsyncMock(return_value="I found 2 relevant rules...")

    return service


_TEST_SID = "test-session"


@pytest.mark.asyncio
async def test_upload_then_explain_flow(chat_service: ChatService) -> None:
    """Test complete flow: upload YAML to session → explain rule."""
    yaml_content = b"""
id: test_001
name: Test Rule
description: A test rule
detection:
    selection:
        EventID: 4625
"""
    rule_data = await chat_service.validate_and_store_yaml(yaml_content, _TEST_SID)
    assert rule_data.id == "test_001"

    response = await chat_service._handle_explain("explain this rule", "", _TEST_SID)
    assert "detects failed login" in response.lower()
    chat_service.rag_pipeline.explain_rule.assert_called_once()


@pytest.mark.asyncio
async def test_search_flow(chat_service: ChatService) -> None:
    """Test search mode flow with LLM response."""
    chat_service.search_engine.search = AsyncMock(
        return_value=[
            {"text": "Rule 1 content", "citation": "sigma:rule_1", "score": 0.95},
            {"text": "Rule 2 content", "citation": "sigma:rule_2", "score": 0.85},
        ]
    )

    chat_service.rag_pipeline.answer_search_query = AsyncMock(
        return_value="I found 2 relevant rules..."
    )

    response = await chat_service._handle_search("failed logon events", "")
    assert "found" in response.lower()
    chat_service._execute_tool_calls.assert_called_once()


@pytest.mark.asyncio
async def test_coverage_flow(chat_service: ChatService) -> None:
    """Test coverage analysis flow."""
    chat_service._set_rule(_TEST_SID, _make_test_rule())

    chat_service.search_engine.search = AsyncMock(
        return_value=[
            {"text": "Related rule 1", "citation": "sigma:rule_2"},
        ]
    )

    chat_service.rag_pipeline.analyze_coverage = AsyncMock(return_value="Coverage analysis: ...")

    response = await chat_service._handle_coverage("check coverage", "", _TEST_SID)
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
    await chat_service.validate_and_store_yaml(yaml_content, _TEST_SID)
    chat_service.rag_pipeline.cache.invalidate.assert_called_once()


@pytest.mark.asyncio
async def test_fallback_when_llm_unavailable(chat_service: ChatService) -> None:
    """Test fallback responses when LLM fails."""
    chat_service.rag_pipeline.answer_search_query = AsyncMock(side_effect=Exception("LLM down"))

    chat_service.search_engine.search = AsyncMock(
        return_value=[
            {"text": "Some rule content", "score": 0.9},
        ]
    )

    response = await chat_service._handle_search("test query", "")
    assert response != ""
    assert "Some rule content" in response or "rule" in response.lower()
