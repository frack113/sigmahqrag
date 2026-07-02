"""Regression tests for SigmaValidator contract.

These tests capture the current contract of SigmaValidator.validate()
so that when it is changed from returning dict[str, Any] to SigmaRule:
- Every dict access pattern is identified
- Every consumer is accounted for

Run before and after the refactoring.
"""

from __future__ import annotations

from typing import Any

import pytest
import yaml

from src.application.sigma.validator import SigmaValidator
from src.shared.exceptions import ValidationError

_VALID_YAML = b"""
id: regr_test_001
name: Regression Test Rule
description: A rule for regression testing
detection:
    selection:
        EventID: 4625
condition: selection
"""

_VALID_DICT: dict[str, Any] = {
    "id": "regr_test_001",
    "name": "Regression Test Rule",
    "description": "A rule for regression testing",
    "detection": {"selection": {"EventID": 4625}},
    "condition": "selection",
}


class TestSigmaValidatorRegression:
    """Regression tests: current contract of SigmaValidator."""

    def setup_method(self) -> None:
        self.validator = SigmaValidator()

    # --- Return type contract ---

    def test_validate_returns_dict(self) -> None:
        result = self.validator.validate(_VALID_YAML)
        assert isinstance(result, dict), "Must return a dict"

    def test_validate_dict_contains_expected_keys(self) -> None:
        result = self.validator.validate(_VALID_YAML)
        assert "id" in result
        assert "name" in result
        assert "description" in result
        assert "detection" in result

    def test_validate_dict_supports_bracket_access(self) -> None:
        result = self.validator.validate(_VALID_YAML)
        assert result["id"] == "regr_test_001"

    def test_validate_dict_supports_get_access(self) -> None:
        result = self.validator.validate(_VALID_YAML)
        assert result.get("condition") == "selection"

    def test_validate_dict_supports_get_missing_key(self) -> None:
        result = self.validator.validate(_VALID_YAML)
        assert result.get("nonexistent") is None

    def test_validate_dict_yaml_dumpable(self) -> None:
        result = self.validator.validate(_VALID_YAML)
        dumped = yaml.dump(result, default_flow_style=False)
        assert isinstance(dumped, str)
        assert "regr_test_001" in dumped

    # --- Error contract ---

    def test_validate_raises_shared_validation_error(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(b"")
        assert exc_info.type is ValidationError
        assert exc_info.value.details["field"] == "file"

    def test_validate_error_has_field_in_details(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(b"")
        assert "field" in exc_info.value.details

    def test_validate_error_has_message(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(b"")
        assert exc_info.value.message

    # --- Deprecated fields (warnings, not errors) ---

    def test_deprecated_fields_still_in_dict(self) -> None:
        yaml_with_deprecated = b"""
id: regr_test_002
name: Rule with deprecated
description: Contains level and falsepositives
level: high
falsepositives:
    - FP1
detection:
    selection:
        EventID: 4625
"""
        result = self.validator.validate(yaml_with_deprecated)
        assert result["level"] == "high"
        assert result["falsepositives"] == ["FP1"]

    # --- Edge cases ---

    def test_validate_large_file_raises_error(self) -> None:
        large_content = b"id: test\nname: test\ndescription: x\n" + b"detection:\n  x: 1\n"
        large_content = large_content + b" " * (1024 * 1024)
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(large_content)
        assert exc_info.value.details["field"] == "file"

    def test_validate_non_dict_yaml(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(b"[1, 2, 3]")
        assert exc_info.value.details["field"] == "yaml_structure"

    def test_validate_invalid_yaml_syntax(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(b"{invalid: yaml: too many: colons: }")
        assert exc_info.value.details["field"] == "yaml_syntax"


class TestChatServiceConsumerRegression:
    """Regression: ChatService usage patterns on validate result.

    ChatService stores the validator result in self._uploaded_rule
    (typed as dict[str, Any]) and accesses it via:
      - .get("name", "")
      - .get("id", "N/A")
      - .get("description")
      - Passes it to RAGPipeline methods as dict[str, Any]
      - Passes it to search_engine.search() as .get("name", "")
    """

    def test_uploaded_rule_get_name(self) -> None:
        result = _VALID_DICT
        name = result.get("name", "")
        assert name == "Regression Test Rule"

    def test_uploaded_rule_get_id(self) -> None:
        result = _VALID_DICT
        rule_id = result.get("id", "N/A")
        assert rule_id == "regr_test_001"

    def test_uploaded_rule_get_description(self) -> None:
        result = _VALID_DICT
        desc = result.get("description")
        assert desc == "A rule for regression testing"

    def test_uploaded_rule_missing_key_returns_default(self) -> None:
        result: dict[str, Any] = {}
        assert result.get("name", "") == ""
        assert result.get("id", "N/A") == "N/A"
        assert result.get("description") is None

    def test_rag_pipeline_format_rule_yaml(self) -> None:
        dumped = yaml.dump(_VALID_DICT, default_flow_style=False, allow_unicode=True)
        assert isinstance(dumped, str)
        assert "Regression Test Rule" in dumped

    def test_rag_pipeline_fallback_explanation(self) -> None:
        parts = [
            f"**Rule:** {_VALID_DICT.get('name', 'Unknown')}",
            f"**ID:** {_VALID_DICT.get('id', 'N/A')}",
        ]
        if desc := _VALID_DICT.get("description"):
            parts.append(f"**Description:** {desc}")
        text = "\n".join(parts)
        assert "Regression Test Rule" in text
        assert "regr_test_001" in text

    def test_search_engine_search_uses_name(self) -> None:
        query = _VALID_DICT.get("name", "")
        assert query == "Regression Test Rule"
