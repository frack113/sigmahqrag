"""Test Sigma rule model."""

from src.shared.schemas.sigma_rule import SigmaRule


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
