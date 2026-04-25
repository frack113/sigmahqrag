"""Tests for document ingestion module."""

from __future__ import annotations

import os
from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from src.auth.security import create_access_token
from src.main import create_app
from src.documents.models import SigmaRule, ValidationError, ValidationResult
from src.documents.parser import parse_sigma_rule, scan_directory
from src.documents.validator import validate_sigma_rule


FIXTURES_DIR = Path(__file__).parent / "fixtures"

os.environ.setdefault("JWT_SECRET", "test-secret-key-for-testing-only")


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
    """Test documents API endpoint."""

    @pytest.fixture
    def client(self) -> TestClient:
        """Create test client."""
        app = create_app()
        return TestClient(app)

    @pytest.fixture
    def admin_token(self) -> str:
        """Create admin JWT token."""
        return create_access_token(
            data={"sub": "admin", "role": "Admin"},
            expires_delta=timedelta(hours=1),
        )

    @pytest.fixture
    def analyst_token(self) -> str:
        """Create analyst JWT token."""
        return create_access_token(
            data={"sub": "analyst", "role": "Analyst"},
            expires_delta=timedelta(hours=1),
        )

    def test_ingest_requires_auth(self, client: TestClient) -> None:
        """Test that ingest requires authentication."""
        response = client.post("/documents/ingest")

        assert response.status_code == 401

    def test_ingest_requires_admin(self, client: TestClient, analyst_token: str) -> None:
        """Test that ingest requires admin role."""
        response = client.post(
            "/documents/ingest",
            headers={"Authorization": f"Bearer {analyst_token}"},
        )

        assert response.status_code == 403

    @patch("src.api.routes.documents.scan_directory")
    @patch("src.api.routes.documents.index_sigma_rules")
    def test_ingest_success(
        self,
        mock_index: AsyncMock,
        mock_scan: AsyncMock,
        client: TestClient,
        admin_token: str,
    ) -> None:
        """Test successful ingestion."""
        mock_scan.return_value = [str(FIXTURES_DIR / "valid_sigma_rule.yml")]
        mock_index.return_value = {"success": True, "indexed": 1}

        response = client.post(
            "/documents/ingest",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"directory": str(FIXTURES_DIR), "recursive": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["successful"] >= 1

    @patch("src.api.routes.documents.scan_directory")
    def test_ingest_no_files(
        self,
        mock_scan: AsyncMock,
        client: TestClient,
        admin_token: str,
    ) -> None:
        """Test ingestion with no files found."""
        mock_scan.return_value = []

        response = client.post(
            "/documents/ingest",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"directory": "/empty/dir"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 0


class TestQdrantIndexing:
    """Test Qdrant indexing."""

    @pytest.mark.asyncio
    @patch("src.documents.indexing.get_config")
    @patch("src.documents.indexing.QdrantService")
    async def test_index_sigma_rules(
        self,
        mock_qdrant: type,
        mock_config: type,
    ) -> None:
        """Test indexing Sigma rules."""
        from src.documents.indexing import index_sigma_rules

        mock_config.return_value = {
            "qdrant_url": "127.0.0.1:6333",
            "qdrant_collection": "test",
            "embed_model": "default",
        }

        mock_service = AsyncMock()
        mock_service.initialize = AsyncMock()
        mock_service.add_vectors = AsyncMock()
        mock_qdrant.return_value = mock_service

        rules = [
            SigmaRule(
                id="test-001",
                title="Test",
                detection={"selection": {"EventID": 4688}},
                condition="selection",
            )
        ]

        result = await index_sigma_rules(rules)

        assert result["success"] is True