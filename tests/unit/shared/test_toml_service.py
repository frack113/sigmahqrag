"""Tests for TOML configuration service."""

from pathlib import Path
from unittest.mock import patch


from src.shared.toml_service import TOMLService, _remove_none_values, deep_merge


class TestRemoveNoneValues:
    def test_removes_none_from_dict(self) -> None:
        result = _remove_none_values({"a": 1, "b": None, "c": "hello"})
        assert result == {"a": 1, "c": "hello"}

    def test_removes_none_nested(self) -> None:
        result = _remove_none_values({"a": {"b": None, "c": 2}, "d": None})
        assert result == {"a": {"c": 2}}

    def test_removes_none_from_list(self) -> None:
        result = _remove_none_values([1, None, 2, None, 3])
        assert result == [1, 2, 3]

    def test_preserves_empty_structures(self) -> None:
        result = _remove_none_values({})
        assert result == {}

    def test_preserves_primitives(self) -> None:
        result = _remove_none_values(42)
        assert result == 42

    def test_handles_mixed_nested(self) -> None:
        result = _remove_none_values({"a": [1, None, {"b": None, "c": 3}], "d": None})
        assert result == {"a": [1, {"c": 3}]}


class TestDeepMerge:
    def test_override_scalar(self) -> None:
        base = {"a": 1, "b": 2}
        deep_merge(base, {"b": 3})
        assert base == {"a": 1, "b": 3}

    def test_merge_nested(self) -> None:
        base = {"a": {"x": 1, "y": 2}, "b": 3}
        deep_merge(base, {"a": {"y": 99, "z": 100}})
        assert base == {"a": {"x": 1, "y": 99, "z": 100}, "b": 3}

    def test_add_new_key(self) -> None:
        base = {"a": 1}
        deep_merge(base, {"b": 2})
        assert base == {"a": 1, "b": 2}

    def test_merge_empty_override(self) -> None:
        base = {"a": 1, "b": 2}
        deep_merge(base, {})
        assert base == {"a": 1, "b": 2}

    def test_merge_empty_base(self) -> None:
        base: dict = {}
        deep_merge(base, {"a": 1})
        assert base == {"a": 1}


class TestTOMLService:
    def test_load_returns_empty_when_file_missing(self, tmp_path: Path) -> None:
        svc = TOMLService(tmp_path / "nonexistent.toml")
        result = svc.load()
        assert result == {}

    def test_load_and_cache(self, tmp_path: Path) -> None:
        toml_file = tmp_path / "config.toml"
        toml_file.write_text('key = "value"\n', encoding="utf-8")
        svc = TOMLService(toml_file)

        result1 = svc.load()
        assert result1 == {"key": "value"}

        toml_file.write_text('key = "changed"\n', encoding="utf-8")
        result2 = svc.load(use_cache=True)
        assert result2["key"] == "value"

    def test_load_no_cache(self, tmp_path: Path) -> None:
        toml_file = tmp_path / "config.toml"
        toml_file.write_text('key = "value"\n', encoding="utf-8")
        svc = TOMLService(toml_file)

        svc.load()
        toml_file.write_text('key = "changed"\n', encoding="utf-8")
        result = svc.load(use_cache=False)
        assert result["key"] == "changed"

    def test_save_and_reload(self, tmp_path: Path) -> None:
        toml_file = tmp_path / "config.toml"
        svc = TOMLService(toml_file)

        saved = svc.save({"name": "test", "count": 42})
        assert saved is True
        assert toml_file.exists()

        loaded = svc.load(use_cache=False)
        assert loaded.get("name") == "test"
        assert loaded.get("count") == 42

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        nested = tmp_path / "sub" / "nested" / "config.toml"
        svc = TOMLService(nested)
        saved = svc.save({"key": "val"})
        assert saved is True
        assert nested.exists()

    def test_save_strips_none_values(self, tmp_path: Path) -> None:
        toml_file = tmp_path / "config.toml"
        svc = TOMLService(toml_file)
        svc.save({"a": 1, "b": None})
        loaded = svc.load(use_cache=False)
        assert "a" in loaded
        assert "b" not in loaded

    def test_save_invalidates_cache(self, tmp_path: Path) -> None:
        toml_file = tmp_path / "config.toml"
        toml_file.write_text('key = "old"\n', encoding="utf-8")
        svc = TOMLService(toml_file)
        svc.load()

        svc.save({"key": "new"})
        result = svc.load()
        assert result["key"] == "new"

    def test_save_keep_cache(self, tmp_path: Path) -> None:
        toml_file = tmp_path / "config.toml"
        svc = TOMLService(toml_file)
        svc.save({"key": "val"}, invalidate_cache=False)
        assert svc._cache is None

    def test_load_returns_empty_on_corrupt_file(self, tmp_path: Path) -> None:
        toml_file = tmp_path / "bad.toml"
        toml_file.write_text("{invalid", encoding="utf-8")
        svc = TOMLService(toml_file)
        result = svc.load()
        assert result == {}

    def test_save_returns_false_on_error(self, tmp_path: Path) -> None:
        svc = TOMLService(tmp_path / "config.toml")
        with patch("src.shared.toml_service.tomli_w.dump", side_effect=PermissionError("denied")):
            result = svc.save({"key": "val"})
            assert result is False
