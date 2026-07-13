"""Regression tests for SigmaValidator contract.

These tests capture the contract of SigmaValidator.validate()
after the refactoring from dict[str, Any] to SigmaRule.
"""

from __future__ import annotations

import pytest
import yaml

from src.application.sigma.validator import SigmaValidator
from src.core.sigma.models import SigmaRule
from src.shared.exceptions import ValidationError

_VALID_YAML = b"""
id: regr_test_001
title: Regression Test Rule
description: A rule for regression testing
detection:
    selection:
        EventID: 4625
condition: selection
"""

_VALID_YAML_WITH_NAME = b"""
id: regr_test_002
name: Name-Based Rule
description: A rule using name instead of title
detection:
    selection:
        EventID: 4625
condition: selection
"""


class TestSigmaValidatorRegression:
    """Regression tests: updated contract of SigmaValidator."""

    def setup_method(self) -> None:
        self.validator = SigmaValidator()

    # --- Return type contract ---

    def test_validate_returns_sigma_rule(self) -> None:
        result = self.validator.validate(_VALID_YAML)
        assert isinstance(result, SigmaRule), "Must return a SigmaRule"

    def test_validate_rule_has_expected_attributes(self) -> None:
        result = self.validator.validate(_VALID_YAML)
        assert result.id == "regr_test_001"
        assert result.title == "Regression Test Rule"
        assert result.name == "Regression Test Rule"
        assert result.description == "A rule for regression testing"
        assert "selection" in result.detection

    def test_validate_rule_supports_name_property(self) -> None:
        result = self.validator.validate(_VALID_YAML)
        assert result.name == result.title

    def test_validate_rule_yaml_dumpable(self) -> None:
        result = self.validator.validate(_VALID_YAML)
        dumped = yaml.dump(result.to_dict(), default_flow_style=False)
        assert isinstance(dumped, str)
        assert "regr_test_001" in dumped

    def test_validate_accepts_name_instead_of_title(self) -> None:
        result = self.validator.validate(_VALID_YAML_WITH_NAME)
        assert isinstance(result, SigmaRule)
        assert result.title == "Name-Based Rule"
        assert result.name == "Name-Based Rule"

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

    def test_deprecated_fields_still_in_rule(self) -> None:
        yaml_with_deprecated = b"""
id: regr_test_003
title: Rule with deprecated
description: Contains level and falsepositives
level: high
falsepositives:
    - FP1
detection:
    selection:
        EventID: 4625
"""
        result = self.validator.validate(yaml_with_deprecated)
        assert result.level == "high"
        assert result.falsepositives == ["FP1"]

    # --- Level validation ---

    def test_invalid_level_raises_error(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(b"""
id: test-001
title: Test
description: Invalid level
level: invalid_level
detection:
  selection:
    EventID: 1
""")
        assert exc_info.value.details["field"] == "level"

    def test_valid_levels_accepted(self) -> None:
        for level in ("informational", "low", "medium", "high", "critical"):
            result = self.validator.validate(
                f"""id: test-001
title: Test {level}
description: Testing level {level}
level: {level}
detection:
  selection:
    EventID: 1
condition: selection
""".encode()
            )
            assert result.level == level

    # --- Status validation ---

    def test_invalid_status_raises_error(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            self.validator.validate(b"""
id: test-001
title: Test
description: Invalid status
status: unknown_status
detection:
  selection:
    EventID: 1
""")
        assert exc_info.value.details["field"] == "status"

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
    """Regression: ChatService usage patterns on SigmaRule.

    After the refactoring, ChatService._uploaded_rule is SigmaRule | None
    and is accessed via:
      - .name (was .get("name", ""))
      - .id (was .get("id", "N/A"))
      - .description (was .get("description"))
    """

    def _make_rule(self) -> SigmaRule:
        return SigmaRule(
            id="regr_test_001",
            title="Regression Test Rule",
            description="A rule for regression testing",
            detection={"selection": {"EventID": 4625}},
            condition="selection",
        )

    def test_uploaded_rule_name(self) -> None:
        rule = self._make_rule()
        assert rule.name == "Regression Test Rule"

    def test_uploaded_rule_id(self) -> None:
        rule = self._make_rule()
        assert rule.id == "regr_test_001"

    def test_uploaded_rule_description(self) -> None:
        rule = self._make_rule()
        assert rule.description == "A rule for regression testing"

    def test_rag_pipeline_format_rule_yaml(self) -> None:
        rule = self._make_rule()
        dumped = yaml.dump(rule.to_dict(), default_flow_style=False, allow_unicode=True)
        assert isinstance(dumped, str)
        assert "regr_test_001" in dumped

    def test_rag_pipeline_fallback_explanation(self) -> None:
        rule = self._make_rule()
        parts = [
            f"**Rule:** {rule.name}",
            f"**ID:** {rule.id}",
        ]
        if rule.description:
            parts.append(f"**Description:** {rule.description}")
        text = "\n".join(parts)
        assert "Regression Test Rule" in text
        assert "regr_test_001" in text

    def test_search_engine_search_uses_name(self) -> None:
        rule = self._make_rule()
        query = rule.name
        assert query == "Regression Test Rule"
