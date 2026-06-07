"""Tests for Sigma rule schema properties."""

import os
from pathlib import Path

from src.core.sigma.models import SigmaRule


class TestSigmaRulePath:
    def test_path_property_with_file_path(self) -> None:
        rule = SigmaRule(
            id="test-001",
            title="Test",
            detection={"condition": "test"},
            file_path="/path/to/rule.yaml",
        )
        assert isinstance(rule.path, Path)
        assert str(rule.path) == os.path.normpath("/path/to/rule.yaml")

    def test_path_property_none(self) -> None:
        rule = SigmaRule(
            id="test-001",
            title="Test",
            detection={"condition": "test"},
        )
        assert rule.path is None

    def test_to_dict_excludes_none(self) -> None:
        rule = SigmaRule(id="test-001", title="Test", detection={"condition": "test"})
        d = rule.to_dict()
        assert "status" not in d
        assert "level" not in d

    def test_to_dict_includes_set_fields(self) -> None:
        rule = SigmaRule(
            id="test-001",
            title="Test",
            detection={"condition": "test"},
            status="stable",
            level="high",
        )
        d = rule.to_dict()
        assert d["status"] == "stable"
        assert d["level"] == "high"
