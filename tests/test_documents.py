"""Tests for document ingestion module."""

import os
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.back.documents.models import SigmaRule
from src.back.documents.parser import parse_sigma_rule, scan_directory
from src.back.documents.validator import validate_sigma_rule
from src.main import create_app

FIXTURES_DIR = Path(__file__).parent / "fixtures"

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


class TestSigmaRuleValidator:
    """Test Sigma rule validator."""

    def test_validate_valid_rule(self) -> None:
        """Test validating a valid rule."""
        rule = SigmaRule(
            id="test-001",
            title="Test Rule",
            detection={"selection": {"EventID": 4688}},
            condition="selection",
            level="high",
        )

        result = validate_sigma_rule(rule)

        assert result.valid is True
        assert result.rule is not None
        assert len(result.errors) == 0

    def test_validate_missing_title(self) -> None:
        """Test validating rule with missing title."""
        rule = SigmaRule(
            id="test-001",
            title="",
            detection={"selection": {"EventID": 4688}},
            condition="selection",
        )

        result = validate_sigma_rule(rule)

        assert result.valid is False
        assert any(e.field == "title" for e in result.errors)

    def test_validate_missing_condition(self) -> None:
        """Test validating rule with missing condition."""
        rule = SigmaRule(
            id="test-001",
            title="Test",
            detection={"selection": {"EventID": 4688}},
            condition="",
        )

        result = validate_sigma_rule(rule)

        assert result.valid is False
        assert any(e.field == "condition" for e in result.errors)

    def test_validate_invalid_level(self) -> None:
        """Test validating rule with invalid level."""
        rule = SigmaRule(
            id="test-001",
            title="Test",
            detection={"selection": {"EventID": 4688}},
            condition="selection",
            level="invalid_level",
        )

        result = validate_sigma_rule(rule)

        assert result.valid is False
        assert any(e.field == "level" for e in result.errors)

    def test_validate_valid_levels(self) -> None:
        """Test validating rule with valid levels."""
        valid_levels = ["informational", "low", "medium", "high", "critical"]

        for level in valid_levels:
            rule = SigmaRule(
                id="test-001",
                title="Test",
                detection={"selection": {"EventID": 4688}},
                condition="selection",
                level=level,
            )

            result = validate_sigma_rule(rule)
            assert result.valid is True, f"Level {level} should be valid"


class TestDocumentsEndpoint:
    """Test document endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        app = create_app()
        os.environ["SIGMA_RULES_DIR"] = str(FIXTURES_DIR)
        return TestClient(app)

    @patch("src.api.v1.documents.scan_directory")
    @patch("src.api.v1.documents.index_sigma_rules")
    def test_ingest_success(
        self,
        mock_index: AsyncMock,
        mock_scan: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test successful ingestion (open in v0.1.0)."""
        mock_scan.return_value = []
        response = client.post("/documents/ingest")

        assert response.status_code == 200
        data = response.json()
        # Accept any valid response
        assert "results" in data or "total_files" in data

    @patch("src.api.routes.documents.scan_directory")
    def test_ingest_no_files(
        self,
        mock_scan: AsyncMock,
        client: TestClient,
    ) -> None:
        """Test ingestion with no files found."""
        mock_scan.return_value = []

        response = client.post(
            "/documents/ingest",
            json={"directory": str(FIXTURES_DIR), "recursive": False},
        )

        assert response.status_code == 200
