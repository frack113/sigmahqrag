"""Tests for document ingestion module."""

import os
from pathlib import Path


from src.application.documents.parser import parse_sigma_rule, scan_directory

FIXTURES_DIR = (Path(__file__).parent / ".." / ".." / ".." / "fixtures").resolve()

os.environ.setdefault("SIGMA_RULES_DIR", str(FIXTURES_DIR))


class TestSigmaRuleParser:
    """Test Sigma rule parser."""

    def test_parse_valid_sigma_rule(self) -> None:
        """Test parsing a valid Sigma rule."""
        rule = parse_sigma_rule(str(FIXTURES_DIR / "valid_sigma_rule.yml"))

        assert rule is not None
        assert rule.id == "test-rule-001"
        assert rule.title == "Test Rule 1"
        assert "EventID" in str(rule.detection)
        assert rule.condition == "selection"
        assert rule.level == "high"

    def test_parse_invalid_file(self) -> None:
        """Test parsing an invalid file."""
        rule = parse_sigma_rule(str(FIXTURES_DIR / "invalid_missing_fields.yml"))

        assert rule is None

    def test_parse_nonexistent_file(self) -> None:
        """Test parsing a nonexistent file."""
        rule = parse_sigma_rule("/path/to/nonexistent.yml")

        assert rule is None

    def test_scan_directory(self) -> None:
        """Test scanning directory for Sigma rules."""
        files = scan_directory(str(FIXTURES_DIR), recursive=False)

        assert len(files) >= 2
        assert any("valid_sigma_rule.yml" in f for f in files)

    def test_scan_empty_directory(self) -> None:
        """Test scanning empty directory."""
        files = scan_directory("/nonexistent/directory")

        assert files == []
