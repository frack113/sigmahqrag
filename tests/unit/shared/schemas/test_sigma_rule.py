"""Test Sigma rule model."""

from pathlib import Path

from src.core.sigma.models import SigmaRule


def test_sigma_rule_model_init() -> None:
    """Test SigmaRule initialization."""
    rule = SigmaRule(
        id="test-001",
        title="Test Rule",
        detection={"condition": "test"},
    )
    assert rule.id == "test-001"
    assert rule.title == "Test Rule"
    assert rule.tags == []


def test_sigma_rule_model_with_tags() -> None:
    """Test SigmaRule with tags."""
    rule = SigmaRule(
        id="test-001",
        title="Test Rule",
        detection={"condition": "test"},
        tags=["tag1", "tag2"],
    )
    assert rule.tags == ["tag1", "tag2"]


def test_from_dict_with_file_path() -> None:
    """Test from_dict with file_path and line_number."""
    data = {"id": "r1", "title": "Rule", "detection": {"condition": "any"}}
    rule = SigmaRule.from_dict(data, file_path=Path("path/to/rule.yml"), line_number=42)
    assert rule.file_path is not None
    assert rule.file_path.endswith("rule.yml")
    assert rule.line_number == 42


def test_from_dict_without_optional() -> None:
    """Test from_dict without optional args."""
    data = {"id": "r2", "title": "Rule 2", "detection": {"condition": "all"}}
    rule = SigmaRule.from_dict(data)
    assert rule.file_path is None
    assert rule.line_number is None


def test_to_dict_excludes_none() -> None:
    """Test to_dict excludes None values."""
    rule = SigmaRule(id="r3", title="R", detection={"c": "t"})
    d = rule.to_dict()
    assert "file_path" not in d
    assert "line_number" not in d


def test_path_property() -> None:
    """Test path property."""
    rule = SigmaRule(id="r4", title="R", detection={"c": "t"}, file_path="/path/r.yml")
    assert rule.path == Path("/path/r.yml")
    rule2 = SigmaRule(id="r5", title="R2", detection={"c": "t"})
    assert rule2.path is None
