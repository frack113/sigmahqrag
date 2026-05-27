"""Tests for SigmaValidator."""

from __future__ import annotations

import pytest
from src.back.backend.services.sigma_validator import MAX_FILE_SIZE, SigmaValidator
from src.shared.exceptions import ValidationError


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


def test_validate_yaml_not_dict() -> None:
    """Test validation fails when YAML is not a mapping."""
    validator = SigmaValidator()
    content = b"just a string"
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(content)
    assert exc_info.value.details["field"] == "yaml_structure"


def test_validate_detection_empty_dict() -> None:
    """Test validation fails when detection is empty."""
    validator = SigmaValidator()
    content = b"""
id: test_rule_005
name: Rule
description: desc
detection: {}
"""
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(content)
    assert exc_info.value.details["field"] == "detection"


def test_validate_empty_id() -> None:
    """Test validation fails when id is empty string."""
    validator = SigmaValidator()
    content = b"""
id: ""
name: Rule
description: desc
detection:
    selection:
        EventID: 4625
"""
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(content)
    assert exc_info.value.details["field"] == "id"


def test_validate_empty_name() -> None:
    """Test validation fails when name is missing or empty."""
    validator = SigmaValidator()
    content = b"""
id: rule_001
name: ""
description: desc
detection:
    selection:
        EventID: 4625
"""
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(content)
    assert exc_info.value.details["field"] == "name"


def test_validate_empty_description() -> None:
    """Test validation fails when description is missing or empty."""
    validator = SigmaValidator()
    content = b"""
id: rule_001
name: Rule
description: ""
detection:
    selection:
        EventID: 4625
"""
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(content)
    assert exc_info.value.details["field"] == "description"


def test_validate_deprecated_fields(caplog: pytest.LogCaptureFixture) -> None:
    """Test that deprecated fields log a warning."""
    validator = SigmaValidator()
    content = b"""
id: rule_001
name: Rule
description: desc
detection:
    selection:
        EventID: 4625
level: high
falsepositives:
    - none
"""
    with caplog.at_level("WARNING"):
        validator.validate(content)
    assert "Deprecated field 'level'" in caplog.text
    assert "Deprecated field 'falsepositives'" in caplog.text


def test_validate_condition_bad_reference(caplog: pytest.LogCaptureFixture) -> None:
    """Test condition referencing non-existent detection key logs warning."""
    validator = SigmaValidator()
    content = b"""
id: rule_001
name: Rule
description: desc
detection:
    selection:
        EventID: 4625
condition: bad_ref
"""
    with caplog.at_level("WARNING"):
        validator.validate(content)
    assert "non-existent detection keys" in caplog.text


def test_validate_condition_ok() -> None:
    """Test valid condition passes without warning."""
    validator = SigmaValidator()
    content = b"""
id: rule_001
name: Rule
description: desc
detection:
    selection:
        EventID: 4625
condition: selection
"""
    result = validator.validate(content)
    assert result["condition"] == "selection"


def test_validate_condition_non_string() -> None:
    """Test non-string condition is silently accepted."""
    validator = SigmaValidator()
    content = b"""
id: rule_001
name: Rule
description: desc
detection:
    selection:
        EventID: 4625
condition: true
"""
    result = validator.validate(content)
    assert result["condition"] is True
