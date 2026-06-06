"""Tests for is_sigma_rule_* heuristic functions."""

import yaml

from src.shared.schemas.sigma_rule import (
    is_sigma_rule,
    is_sigma_rule_candidate,
    is_sigma_rule_content,
    is_sigma_rule_dict,
    is_sigma_rule_path,
)


# ---- is_sigma_rule_dict ----


class TestIsSigmaRuleDict:
    """Tests for the canonical strict heuristic (Sigma spec)."""

    def test_valid_sigma_rule(self) -> None:
        data = {
            "logsource": {"category": "process_creation"},
            "detection": {"selection": {"Image": "notepad.exe"}},
        }
        assert is_sigma_rule_dict(data) is True

    def test_missing_logsource(self) -> None:
        data = {"detection": {"selection": {"Image": "notepad.exe"}}}
        assert is_sigma_rule_dict(data) is False

    def test_missing_detection(self) -> None:
        data = {"logsource": {"category": "process_creation"}}
        assert is_sigma_rule_dict(data) is False

    def test_empty_dict(self) -> None:
        assert is_sigma_rule_dict({}) is False

    def test_non_dict_is_false(self) -> None:
        assert is_sigma_rule_dict("not a dict") is False
        assert is_sigma_rule_dict(None) is False  # type: ignore[arg-type]
        assert is_sigma_rule_dict([]) is False  # type: ignore[arg-type]

    def test_with_title_and_id(self) -> None:
        data = {
            "id": "e0c3b1e0-0000-0000-0000-000000000000",
            "title": "Test Rule",
            "logsource": {"category": "process_creation"},
            "detection": {"selection": {"Image": "notepad.exe"}},
        }
        assert is_sigma_rule_dict(data) is True

    def test_with_all_sigma_keys(self) -> None:
        data = {
            "id": "e0c3b1e0-0000-0000-0000-000000000000",
            "title": "Test Rule",
            "logsource": {"category": "process_creation"},
            "detection": {"selection": {"Image": "notepad.exe"}},
            "condition": "selection",
        }
        assert is_sigma_rule_dict(data) is True

    def test_ci_config_false_positive(self) -> None:
        """A non-Sigma YAML with logsource + detection keys."""
        data = {
            "logsource": {"category": "build"},
            "detection": {"steps": ["build", "test"]},
        }
        assert is_sigma_rule_dict(data) is True

    def test_minimal_sigma_rule(self) -> None:
        """Sigma spec requires only logsource + detection."""
        data = {"logsource": {}, "detection": {}}
        assert is_sigma_rule_dict(data) is True


# ---- is_sigma_rule_candidate ----


class TestIsSigmaRuleCandidate:
    """Tests for the lenient file-type detection heuristic."""

    def test_valid_rule_with_condition(self) -> None:
        data = {
            "title": "Test Rule",
            "detection": {"selection": {"Image": "notepad.exe"}},
            "condition": "selection",
        }
        assert is_sigma_rule_candidate(data) is True

    def test_rule_with_id_instead_of_title(self) -> None:
        data = {
            "id": "e0c3b1e0-0000-0000-0000-000000000000",
            "detection": {"selection": {"Image": "notepad.exe"}},
            "condition": "selection",
        }
        assert is_sigma_rule_candidate(data) is True

    def test_missing_detection(self) -> None:
        data = {"title": "Test Rule", "condition": "any"}
        assert is_sigma_rule_candidate(data) is False

    def test_missing_title_and_id(self) -> None:
        data = {
            "detection": {"selection": {"Image": "notepad.exe"}},
            "condition": "selection",
        }
        assert is_sigma_rule_candidate(data) is False

    def test_condition_at_top_level(self) -> None:
        data = {"title": "R", "detection": {"s": {"i": "v"}}, "condition": "s"}
        assert is_sigma_rule_candidate(data) is True

    def test_nested_condition_in_detection(self) -> None:
        """Some Sigma rules omit top-level condition and nest it."""
        data = {
            "title": "R",
            "detection": {
                "condition": "all of selection*",
                "selection": {"Image": "notepad.exe"},
            },
        }
        assert is_sigma_rule_candidate(data) is True

    def test_no_condition_top_or_nested(self) -> None:
        data = {"title": "R", "detection": {"selection": {"Image": "notepad.exe"}}}
        assert is_sigma_rule_candidate(data) is False

    def test_empty_condition_string(self) -> None:
        """Empty string is falsy — should check for nested condition."""
        data = {"title": "R", "detection": {"selection": {"Image": "notepad.exe"}}, "condition": ""}
        assert is_sigma_rule_candidate(data) is False

    def test_empty_dict(self) -> None:
        assert is_sigma_rule_candidate({}) is False

    def test_non_dict_is_false(self) -> None:
        assert is_sigma_rule_candidate("str") is False
        assert is_sigma_rule_candidate(None) is False  # type: ignore[arg-type]
        assert is_sigma_rule_candidate([]) is False  # type: ignore[arg-type]

    def test_only_detection_not_enough(self) -> None:
        data = {"detection": {"selection": {"Image": "notepad.exe"}}}
        assert is_sigma_rule_candidate(data) is False

    def test_rule_with_all_fields(self) -> None:
        data = {
            "id": "e0c3b1e0-0000-0000-0000-000000000000",
            "title": "Test Rule",
            "logsource": {"category": "process_creation"},
            "detection": {"selection": {"Image": "notepad.exe"}},
            "condition": "selection",
        }
        assert is_sigma_rule_candidate(data) is True


# ---- is_sigma_rule (dispatcher) ----


class TestIsSigmaRule:
    """Tests for the unified dispatcher."""

    def test_dispatch_dict(self) -> None:
        data = {"logsource": {}, "detection": {}}
        assert is_sigma_rule(data) is True

    def test_dispatch_dict_false(self) -> None:
        data = {"title": "R", "detection": {}}
        assert is_sigma_rule(data) is False

    def test_dispatch_str(self) -> None:
        content = yaml.dump({"logsource": {}, "detection": {}})
        assert is_sigma_rule(content) is True

    def test_dispatch_str_empty(self) -> None:
        assert is_sigma_rule("") is False

    def test_dispatch_bytes(self) -> None:
        content = yaml.dump({"logsource": {}, "detection": {}}).encode("utf-8")
        assert is_sigma_rule(content) is True

    def test_dispatch_path(self, tmp_path: object) -> None:
        from pathlib import Path

        rule_file = Path(str(tmp_path)) / "rule.yml"
        rule_file.write_text(yaml.dump({"logsource": {}, "detection": {}}), encoding="utf-8")
        assert is_sigma_rule(rule_file) is True

    def test_dispatch_path_invalid_yml(self, tmp_path: object) -> None:
        from pathlib import Path

        bad_file = Path(str(tmp_path)) / "bad.yml"
        bad_file.write_text("{{invalid yaml: [}", encoding="utf-8")
        assert is_sigma_rule(bad_file) is False

    def test_dispatch_none_type(self) -> None:
        assert is_sigma_rule(None) is False  # type: ignore[arg-type]

    def test_dispatch_list(self) -> None:
        assert is_sigma_rule([1, 2, 3]) is False


# ---- is_sigma_rule_path / is_sigma_rule_content ----


class TestIsSigmaRulePath:
    """Tests for Path-based detection."""

    def test_valid_yaml(self, tmp_path: object) -> None:
        from pathlib import Path

        rule_file = Path(str(tmp_path)) / "rule.yml"
        rule_file.write_text(
            yaml.dump(
                {"logsource": {"category": "process_creation"}, "detection": {"s": {"i": "v"}}}
            ),
            encoding="utf-8",
        )
        assert is_sigma_rule_path(rule_file) is True

    def test_non_sigma_yaml(self, tmp_path: object) -> None:
        from pathlib import Path

        rule_file = Path(str(tmp_path)) / "config.yml"
        rule_file.write_text("key: value\nother: 42\n", encoding="utf-8")
        assert is_sigma_rule_path(rule_file) is False

    def test_empty_file(self, tmp_path: object) -> None:
        from pathlib import Path

        rule_file = Path(str(tmp_path)) / "empty.yml"
        rule_file.write_text("", encoding="utf-8")
        assert is_sigma_rule_path(rule_file) is False

    def test_nonexistent_file(self, tmp_path: object) -> None:
        from pathlib import Path

        rule_file = Path(str(tmp_path)) / "doesNotExist.yml"
        assert is_sigma_rule_path(rule_file) is False


class TestIsSigmaRuleContent:
    """Tests for string/bytes content detection."""

    def test_valid_sigma_content(self) -> None:
        content = yaml.dump({"logsource": {}, "detection": {}})
        assert is_sigma_rule_content(content) is True

    def test_bytes_content(self) -> None:
        content = yaml.dump({"logsource": {}, "detection": {}}).encode("utf-8")
        assert is_sigma_rule_content(content) is True

    def test_invalid_yaml(self) -> None:
        assert is_sigma_rule_content("{{invalid: [}") is False

    def test_none_content(self) -> None:
        assert is_sigma_rule_content(None) is False  # type: ignore[arg-type]

    def test_list_content(self) -> None:
        assert is_sigma_rule_content("[1, 2, 3]") is False
