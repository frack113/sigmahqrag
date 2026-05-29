"""Tests for uncovered chunker branches."""

from __future__ import annotations

from unittest.mock import patch

from src.back.rag.chunker import _format_detection, chunk_sigma_rule
from src.shared.schemas.sigma_rule import SigmaRule


def test_rule_with_description() -> None:
    rule = SigmaRule(
        id="test-001",
        title="Rule",
        description="A description for the rule",
        detection={"condition": "test"},
    )
    chunks = chunk_sigma_rule(rule)
    assert len(chunks) >= 1
    assert "Description:" in chunks[0].text
    assert "A description for the rule" in chunks[0].text


def test_description_overflow() -> None:
    with patch("src.back.rag.chunker.MAX_TOKENS", 1):
        rule = SigmaRule(
            id="test-001",
            title="Rule",
            description="A very long description" * 20,
            detection={"condition": "test"},
        )
        chunks = chunk_sigma_rule(rule)
        assert len(chunks) >= 1


def test_detection_overflow() -> None:
    with patch("src.back.rag.chunker.MAX_TOKENS", 1):
        rule = SigmaRule(
            id="test-001",
            title="Rule",
            detection={"condition": "test", "selection": {"field": "value"}},
        )
        chunks = chunk_sigma_rule(rule)
        assert len(chunks) >= 1


def test_fields_overflow() -> None:
    with patch("src.back.rag.chunker.MAX_TOKENS", 1):
        rule = SigmaRule(
            id="test-001",
            title="Rule",
            detection={"condition": "test"},
            fields=["field1", "field2"],
        )
        chunks = chunk_sigma_rule(rule)
        assert len(chunks) >= 1


def test_falsepositives_overflow() -> None:
    with patch("src.back.rag.chunker.MAX_TOKENS", 1):
        rule = SigmaRule(
            id="test-001",
            title="Rule",
            detection={"condition": "test"},
            falsepositives=["fp1"],
        )
        chunks = chunk_sigma_rule(rule)
        assert len(chunks) >= 1


def test_empty_format_detection() -> None:
    assert _format_detection({}) == ""


def test_format_detection_with_non_dict_value() -> None:
    result = _format_detection({"condition": "test", "key": "string_value"})
    assert "key: string_value" in result


def test_no_chunks_fallback() -> None:
    rule = SigmaRule(
        id="test-001",
        title="Empty Rule",
        detection={},
        status=None,
        level=None,
    )
    chunks = chunk_sigma_rule(rule)
    assert len(chunks) >= 1
