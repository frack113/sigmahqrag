"""Tests for SigmaValidator."""

from __future__ import annotations

import pytest
from src.core.services.sigma_validator import SigmaValidator, MAX_FILE_SIZE
from src.errors import ValidationError


def test_validate_valid_yaml() -> None:
    """Test validation of valid Sigma rule YAML."""
    validator = SigmaValidator()
    content = b"""
id: test_rule_001
name: Test Rule
description: A test rule
detection:
    selection:
        EventID: 4625
"""
    result = validator.validate(content)
    assert result["id"] == "test_rule_001"
    assert result["name"] == "Test Rule"
    assert "detection" in result


def test_validate_missing_fields() -> None:
    """Test validation fails when required fields are missing."""
    validator = SigmaValidator()
    content = b"""
id: test_rule_002
# missing name, description, detection
"""
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(content)
    assert exc_info.value.details["field"] == "required_fields"


def test_validate_invalid_yaml() -> None:
    """Test validation fails on invalid YAML syntax."""
    validator = SigmaValidator()
    content = b"this: [is: broken: yaml: content"
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(content)
    assert exc_info.value.details["field"] == "yaml_syntax"


def test_validate_empty_file() -> None:
    """Test validation fails on empty content."""
    validator = SigmaValidator()
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(b"")
    assert exc_info.value.details["field"] == "file"


def test_validate_large_file() -> None:
    """Test validation fails on oversized file."""
    validator = SigmaValidator()
    large_content = b"id: big_rule\n" + b"x" * (MAX_FILE_SIZE + 1)
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(large_content)
    assert "too large" in exc_info.value.message


def test_validate_missing_detection() -> None:
    """Test validation fails when detection section is empty."""
    validator = SigmaValidator()
    content = b"""
id: test_rule_003
name: Rule
description: desc
detection:
"""
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(content)
    assert exc_info.value.details["field"] == "detection"


def test_validate_detection_not_dict() -> None:
    """Test validation fails when detection is not a mapping."""
    validator = SigmaValidator()
    content = b"""
id: test_rule_004
name: Rule
description: desc
detection: "not a dict"
"""
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(content)
    assert exc_info.value.details["field"] == "detection"
