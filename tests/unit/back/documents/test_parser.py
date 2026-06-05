"""Tests for Sigma rule document parser."""

from pathlib import Path

import pytest
import yaml

from src.back.documents.parser import parse_yaml_file, parse_sigma_rule, scan_directory


class TestParseYamlFile:
    def test_parses_valid_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yaml"
        f.write_text("title: Test Rule\ndetection:\n  condition: selection\n", encoding="utf-8")
        result = parse_yaml_file(str(f))
        assert result["title"] == "Test Rule"
        assert result["detection"]["condition"] == "selection"

    def test_raises_on_nonexistent_file(self) -> None:
        with pytest.raises(FileNotFoundError, match="not found"):
            parse_yaml_file("/nonexistent/path/rule.yaml")

    def test_raises_on_invalid_extension(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.txt"
        f.write_text("title: test", encoding="utf-8")
        with pytest.raises(ValueError, match="Invalid file extension"):
            parse_yaml_file(str(f))

    def test_raises_on_large_file(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yaml"
        f.write_text("x" * (1024 * 1024 + 1), encoding="utf-8")
        with pytest.raises(ValueError, match="File too large"):
            parse_yaml_file(str(f))

    def test_accepts_yml_extension(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yml"
        f.write_text("title: Test", encoding="utf-8")
        result = parse_yaml_file(str(f))
        assert result["title"] == "Test"


class TestParseSigmaRule:
    def test_parses_valid_rule(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yaml"
        f.write_text(
            "title: Test Rule\ndetection:\n  condition: selection\ncondition: selection\n",
            encoding="utf-8",
        )
        rule = parse_sigma_rule(str(f))
        assert rule is not None
        assert rule.title == "Test Rule"
        assert rule.condition == "selection"

    def test_returns_none_on_file_not_found(self) -> None:
        rule = parse_sigma_rule("/nonexistent.yaml")
        assert rule is None

    def test_returns_none_on_invalid_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yaml"
        f.write_text("invalid: [yaml: broken", encoding="utf-8")
        rule = parse_sigma_rule(str(f))
        assert rule is None

    def test_returns_none_on_missing_title(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yaml"
        f.write_text("detection:\n  condition: selection\n", encoding="utf-8")
        rule = parse_sigma_rule(str(f))
        assert rule is None

    def test_uses_filename_as_id_when_missing(self, tmp_path: Path) -> None:
        f = tmp_path / "my_rule.yaml"
        f.write_text(
            "title: My Rule\ncondition: selection\ndetection:\n  condition: selection\n",
            encoding="utf-8",
        )
        rule = parse_sigma_rule(str(f))
        assert rule is not None
        assert rule.id == "my_rule"

    def test_full_rule_with_all_fields(self, tmp_path: Path) -> None:
        data = {
            "title": "Full Rule",
            "id": "rule-001",
            "detection": {"selection": {"field": "val"}, "condition": "selection"},
            "condition": "selection",
            "description": "A full rule",
            "author": "test",
            "date": "2024-01-01",
            "modified": "2024-06-01",
            "references": ["https://example.com"],
            "tags": ["attack.test"],
            "level": "high",
            "falsepositives": ["none"],
            "logsource": {"category": "process_creation", "product": "windows"},
            "status": "stable",
            "license": "DRL",
        }
        f = tmp_path / "full.yaml"
        f.write_text(yaml.dump(data), encoding="utf-8")
        rule = parse_sigma_rule(str(f))
        assert rule is not None
        assert rule.id == "rule-001"
        assert rule.title == "Full Rule"
        assert rule.description == "A full rule"
        assert rule.author == "test"
        assert rule.status == "stable"
        assert rule.level == "high"

    def test_returns_none_on_non_dict_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yaml"
        f.write_text("- item1\n- item2\n", encoding="utf-8")
        rule = parse_sigma_rule(str(f))
        assert rule is None

    def test_returns_none_on_wrong_types(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yaml"
        data = {
            "title": "Bad Types",
            "detection": {"selection": {"field": "val"}, "condition": "selection"},
            "condition": "selection",
            "references": "not_a_list",
        }
        f.write_text(yaml.dump(data), encoding="utf-8")
        rule = parse_sigma_rule(str(f))
        assert rule is None


class TestScanDirectory:
    def test_scans_all_files(self, tmp_path: Path) -> None:
        (tmp_path / "rule1.yaml").write_text("title: R1", encoding="utf-8")
        (tmp_path / "rule2.yml").write_text("title: R2", encoding="utf-8")
        (tmp_path / "note.txt").write_text("text", encoding="utf-8")

        files = scan_directory(str(tmp_path), recursive=False)
        assert len(files) == 3
        assert any(f.endswith("rule1.yaml") for f in files)
        assert any(f.endswith("rule2.yml") for f in files)
        assert any(f.endswith("note.txt") for f in files)

    def test_recursive_scan(self, tmp_path: Path) -> None:
        sub = tmp_path / "subdir"
        sub.mkdir()
        (tmp_path / "root.yaml").write_text("title: R", encoding="utf-8")
        (sub / "nested.yaml").write_text("title: N", encoding="utf-8")

        files = scan_directory(str(tmp_path), recursive=True)
        assert len(files) == 2

        files_nonrecursive = scan_directory(str(tmp_path), recursive=False)
        assert len(files_nonrecursive) == 1

    def test_returns_empty_for_nonexistent_dir(self) -> None:
        files = scan_directory("/nonexistent/path")
        assert files == []

    def test_returns_empty_for_file_path(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("hello", encoding="utf-8")
        files = scan_directory(str(f))
        assert files == []
