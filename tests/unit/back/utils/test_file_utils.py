"""Tests for file_utils."""

import json
from pathlib import Path

from src.back.utils.file_utils import load_registry_files


class TestLoadRegistryFiles:
    def test_returns_empty_list_when_file_missing(self, tmp_path: Path) -> None:
        result = load_registry_files(tmp_path / "nonexistent.json")
        assert result == []

    def test_loads_entries_with_hash_and_filename(self, tmp_path: Path) -> None:
        registry_file = tmp_path / "registry.json"
        registry_data = {
            "abc123": {"name": "test", "size": 100},
            "def456": {"name": "test2", "size": 200},
        }
        registry_file.write_text(json.dumps(registry_data), encoding="utf-8")

        (tmp_path / "abc123.md").write_text("content", encoding="utf-8")

        result = load_registry_files(registry_file)

        assert len(result) == 2

        entry1 = next(e for e in result if e["hash"] == "abc123")
        assert entry1["name"] == "test"
        assert entry1["size"] == 100
        assert entry1["file_name"] == "abc123.md"
        assert entry1["path"] == str(tmp_path / "abc123.md")

        entry2 = next(e for e in result if e["hash"] == "def456")
        assert entry2["name"] == "test2"
        assert entry2["file_name"] == "def456.md"
        assert entry2["path"] == str(tmp_path / "def456.md")

    def test_loads_entries_with_various_extensions(self, tmp_path: Path) -> None:
        registry_file = tmp_path / "registry.json"
        registry_data = {
            "hash001": {"name": "doc1"},
            "hash002": {"name": "doc2"},
        }
        registry_file.write_text(json.dumps(registry_data), encoding="utf-8")

        (tmp_path / "hash001.pdf").write_text("content", encoding="utf-8")

        result = load_registry_files(registry_file)
        assert len(result) == 2

        entry1 = next(e for e in result if e["hash"] == "hash001")
        assert entry1["file_name"] == "hash001.pdf"
        assert entry1["path"] == str(tmp_path / "hash001.pdf")

        entry2 = next(e for e in result if e["hash"] == "hash002")
        assert entry2["file_name"] == "hash002.md"

    def test_preserves_extra_fields(self, tmp_path: Path) -> None:
        registry_file = tmp_path / "registry.json"
        data = {
            "abc123": {"name": "test", "size": 100, "status": "ready", "tags": ["a", "b"]},
        }
        registry_file.write_text(json.dumps(data), encoding="utf-8")
        result = load_registry_files(registry_file)

        assert len(result) == 1
        entry = result[0]
        assert entry["status"] == "ready"
        assert entry["tags"] == ["a", "b"]

    def test_handles_empty_registry(self, tmp_path: Path) -> None:
        registry_file = tmp_path / "registry.json"
        registry_file.write_text("{}", encoding="utf-8")
        result = load_registry_files(registry_file)
        assert result == []
