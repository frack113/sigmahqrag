"""Advanced tests for SigmaValidator."""

from __future__ import annotations

import pytest
from src.application.sigma.validator import SigmaValidator
from src.shared.exceptions import ValidationError


def test_validate_field_types_invalid_id() -> None:
    """Test validation fails when ID is not a string."""
    validator = SigmaValidator()
    content = b"""
id: 12345
name: Test Rule
description: A test
detection:
    selection:
        EventID: 4625
"""
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(content)
    assert exc_info.value.details["field"] == "id"


def test_validate_field_types_invalid_name() -> None:
    """Test validation fails when name is not a string."""
    validator = SigmaValidator()
    content = b"""
id: test_001
name: [not a string]
description: A test
detection:
    selection:
        EventID: 4625
"""
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(content)
    assert exc_info.value.details["field"] == "name"


def test_validate_deprecated_fields() -> None:
    """Test that deprecated fields generate warnings (not errors)."""
    validator = SigmaValidator()
    content = b"""
id: test_001
name: Test Rule
description: A test
level: high
falsepositives:
    - Known false positive
detection:
    selection:
        EventID: 4625
"""
    # Should not raise - deprecated fields are warnings only
    result = validator.validate(content)
    assert result.level == "high"


def test_validate_condition_syntax() -> None:
    """Test condition syntax validation."""
    validator = SigmaValidator()
    content = b"""
id: test_001
name: Test Rule
description: A test
detection:
    selection:
        EventID: 4625
condition: selection
"""
    # Should not raise - valid condition
    result = validator.validate(content)
    assert result.condition == "selection"


def test_validate_condition_invalid_ref() -> None:
    """Test condition referencing non-existent detection key."""
    validator = SigmaValidator()
    content = b"""
id: test_001
name: Test Rule
description: A test
detection:
    selection:
        EventID: 4625
condition: nonexistent
"""
    # Should log warning but not raise
    result = validator.validate(content)
    assert result.condition == "nonexistent"


def test_validate_empty_description() -> None:
    """Test validation fails when description is empty."""
    validator = SigmaValidator()
    content = b"""
id: test_001
name: Test Rule
description: ""
detection:
    selection:
        EventID: 4625
"""
    with pytest.raises(ValidationError) as exc_info:
        validator.validate(content)
    assert exc_info.value.details["field"] == "description"
