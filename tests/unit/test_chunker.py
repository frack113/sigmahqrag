"""Tests for Sigma rule chunker."""

from pathlib import Path

from src.rag.chunker import (
    SigmaChunker,
    _format_detection,
    chunk_sigma_rule,
    count_tokens,
)
from src.schemas.sigma_rule import SigmaRule


class TestCountTokens:
    """Test token counting."""

    def test_single_word(self):
        """Test single word."""
        assert count_tokens("hello") == 1

    def test_sentence(self):
        """Test sentence."""
        assert count_tokens("hello world test") == 3


class TestFormatDetection:
    """Test detection formatting."""

    def test_simple_condition(self):
        """Test simple condition."""
        detection = {"condition": "test"}
        result = _format_detection(detection)
        assert "Condition: test" in result

    def test_with_selection(self):
        """Test with selection."""
        detection = {
            "condition": "selection",
            "selection": {"field": "value"},
        }
        result = _format_detection(detection)
        assert "selection" in result.lower()


class TestSigmaRuleModel:
    """Test SigmaRule model."""

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "id": "test-001",
            "title": "Test Rule",
            "detection": {"condition": "test"},
            "status": "stable",
            "level": "high",
        }
        rule = SigmaRule.from_dict(data)
        assert rule.id == "test-001"
        assert rule.title == "Test Rule"
        assert rule.status == "stable"
        assert rule.level == "high"

    def test_from_dict_with_path(self):
        """Test creating from dict with dict with file path."""
        data = {"id": "test-001", "title": "Test", "detection": {}}
        rule = SigmaRule.from_dict(data, Path("/path/to/file.yaml"), 10)
        assert rule.file_path == "\\path\\to\\file.yaml"
        assert rule.line_number == 10

    def test_to_dict(self):
        """Test converting to dict."""
        rule = SigmaRule(
            id="test-001",
            title="Test",
            detection={"condition": "test"},
        )
        result = rule.to_dict()
        assert result["id"] == "test-001"
        assert result["title"] == "Test"


class TestChunkSigmaRule:
    """Test chunking Sigma rules."""

    def test_simple_rule_chunks(self):
        """Test simple rule creates at least one chunk."""
        rule = SigmaRule(
            id="test-001",
            title="Simple Test Rule",
            detection={"condition": "test = value"},
            status="stable",
            level="medium",
        )
        chunks = chunk_sigma_rule(rule)
        assert len(chunks) >= 1
        assert chunks[0].text
        assert "Simple Test Rule" in chunks[0].text

    def test_metadata_preserved(self):
        """Test metadata is preserved in chunks."""
        rule = SigmaRule(
            id="test-001",
            title="Test Rule",
            detection={"condition": "test"},
            file_path="\\path\\to\\rules\\test.yaml",
            line_number=10,
        )
        chunks = chunk_sigma_rule(rule)
        assert len(chunks) >= 1
        assert chunks[0].metadata["rule_id"] == "test-001"
        assert chunks[0].metadata["title"] == "Test Rule"
        assert chunks[0].metadata["file_path"] == "\\path\\to\\rules\\test.yaml"
        assert chunks[0].metadata["line_start"] == 10


class TestSigmaChunker:
    """Test SigmaChunker class."""

    def test_init_defaults(self):
        """Test default initialization."""
        chunker = SigmaChunker()
        assert chunker.max_tokens == 512

    def test_init_custom_max_tokens(self):
        """Test custom max tokens."""
        chunker = SigmaChunker(max_tokens=256)
        assert chunker.max_tokens == 256

    def test_chunk_with_fields(self):
        """Test chunking with fields."""
        rule = SigmaRule(
            id="test-001",
            title="Rule With Fields",
            detection={"condition": "field1 = value1"},
            fields=["field1", "field2"],
        )
        chunks = chunk_sigma_rule(rule)
        assert len(chunks) >= 1
        assert "field1, field2" in chunks[0].text

    def test_chunk_with_falsepositives(self):
        """Test chunking with falsepositives."""
        rule = SigmaRule(
            id="test-001",
            title="Rule With FP",
            detection={"condition": "test"},
            falsepositives=["false_positive_1"],
        )
        chunks = chunk_sigma_rule(rule)
        assert len(chunks) >= 1
        assert "false_positive_1" in chunks[0].text
