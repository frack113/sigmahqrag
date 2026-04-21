"""Test Sigma rule model."""

from src.models.sigma_rule import SigmaRuleModel


def test_sigma_rule_model_init() -> None:
    """Test SigmaRuleModel initialization."""
    rule = SigmaRuleModel(
        id="test-001",
        title="Test Rule",
        detection={"condition": "test"},
    )
    assert rule.id == "test-001"
    assert rule.title == "Test Rule"
    assert rule.tags == []


def test_sigma_rule_model_with_tags() -> None:
    """Test SigmaRuleModel with tags."""
    rule = SigmaRuleModel(
        id="test-001",
        title="Test Rule",
        detection={"condition": "test"},
        tags=["tag1", "tag2"],
    )
    assert rule.tags == ["tag1", "tag2"]
