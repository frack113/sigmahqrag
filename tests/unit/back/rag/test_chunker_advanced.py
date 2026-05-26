"""Advanced tests for Sigma rule chunker."""

from pathlib import Path

from src.back.rag.chunker import (
    SigmaChunker,
    load_sigma_rule,
    load_sigma_rules_from_directory,
)


class TestLoadSigmaRule:
    def test_loads_valid_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yaml"
        f.write_text(
            "title: Test Rule\nid: rule-001\ndetection:\n  condition: selection\n",
            encoding="utf-8",
        )
        rules = load_sigma_rule(f)
        assert len(rules) == 1
        assert rules[0].title == "Test Rule"
        assert rules[0].id == "rule-001"

    def test_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.yaml"
        f.write_text("", encoding="utf-8")
        rules = load_sigma_rule(f)
        assert rules == []

    def test_invalid_yaml(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.yaml"
        f.write_text("{invalid: yaml: [broken", encoding="utf-8")
        rules = load_sigma_rule(f)
        assert rules == []

    def test_no_title_field(self, tmp_path: Path) -> None:
        f = tmp_path / "no_title.yaml"
        f.write_text("description: no title here\n", encoding="utf-8")
        rules = load_sigma_rule(f)
        assert rules == []


class TestLoadSigmaRulesFromDirectory:
    def test_loads_matching_files(self, tmp_path: Path) -> None:
        (tmp_path / "r1.yaml").write_text(
            "title: Rule 1\nid: r1\ndetection:\n  condition: selection\n",
            encoding="utf-8",
        )
        (tmp_path / "r2.yaml").write_text(
            "title: Rule 2\nid: r2\ndetection:\n  condition: selection\n",
            encoding="utf-8",
        )
        (tmp_path / "note.txt").write_text("not a rule", encoding="utf-8")
        rules = load_sigma_rules_from_directory(tmp_path, "*.yaml")
        assert len(rules) == 2

    def test_empty_directory(self, tmp_path: Path) -> None:
        rules = load_sigma_rules_from_directory(tmp_path)
        assert rules == []


class TestSigmaChunkerFile:
    def test_chunk_file(self, tmp_path: Path) -> None:
        f = tmp_path / "rule.yaml"
        f.write_text(
            "title: Test Rule\nid: rule-001\ndetection:\n  condition: selection\n",
            encoding="utf-8",
        )
        chunker = SigmaChunker()
        chunks = chunker.chunk_file(f)
        assert len(chunks) >= 1

    def test_chunk_nonexistent_file(self) -> None:
        chunker = SigmaChunker()
        chunks = chunker.chunk_file(Path("/nonexistent/rule.yaml"))
        assert chunks == []

    def test_chunk_directory(self, tmp_path: Path) -> None:
        (tmp_path / "r1.yaml").write_text(
            "title: Rule 1\nid: r1\ndetection:\n  condition: selection\n",
            encoding="utf-8",
        )
        chunker = SigmaChunker()
        chunks = chunker.chunk_directory(tmp_path)
        assert len(chunks) >= 1
