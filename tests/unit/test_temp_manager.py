"""Tests for temporary file manager."""

from pathlib import Path


from src.shared.temp_manager import TempManager, create_temp_manager


class TestTempManager:
    def test_init_defaults(self) -> None:
        mgr = TempManager(temp_dir=Path("/tmp/test"))
        assert mgr.temp_dir == Path("/tmp/test")

    def test_create_temp_file(self, tmp_path: Path) -> None:
        mgr = TempManager(temp_dir=tmp_path)
        result = mgr.create_temp_file("abc-123", extension=".zip")
        assert result == tmp_path / "abc-123.zip"
        assert tmp_path.exists()

    def test_create_temp_file_default_extension(self, tmp_path: Path) -> None:
        mgr = TempManager(temp_dir=tmp_path)
        result = mgr.create_temp_file("abc-123")
        assert result.suffix == ".tmp"

    def test_cleanup_existing_file(self, tmp_path: Path) -> None:
        mgr = TempManager(temp_dir=tmp_path)
        test_file = tmp_path / "test.tmp"
        test_file.write_text("data")

        result = mgr.cleanup(test_file)
        assert result is True
        assert not test_file.exists()

    def test_cleanup_nonexistent_file(self, tmp_path: Path) -> None:
        mgr = TempManager(temp_dir=tmp_path)
        result = mgr.cleanup(tmp_path / "nonexistent.tmp")
        assert result is False

    def test_cleanup_all(self, tmp_path: Path) -> None:
        mgr = TempManager(temp_dir=tmp_path)
        (tmp_path / "file1.tmp").write_text("data1")
        (tmp_path / "file2.tmp").write_text("data2")
        (tmp_path / "file3.txt").write_text("data3")

        count = mgr.cleanup_all()
        assert count == 3
        assert not any(tmp_path.iterdir())

    def test_cleanup_all_ignores_dirs(self, tmp_path: Path) -> None:
        mgr = TempManager(temp_dir=tmp_path)
        (tmp_path / "file.tmp").write_text("data")
        (tmp_path / "subdir").mkdir()

        count = mgr.cleanup_all()
        assert count == 1

    def test_cleanup_all_empty_dir(self, tmp_path: Path) -> None:
        mgr = TempManager(temp_dir=tmp_path)
        count = mgr.cleanup_all()
        assert count == 0

    def test_cleanup_all_nonexistent_dir(self, tmp_path: Path) -> None:
        mgr = TempManager(temp_dir=tmp_path / "nonexistent")
        count = mgr.cleanup_all()
        assert count == 0

    def test_create_temp_file_creates_dir(self, tmp_path: Path) -> None:
        nested = tmp_path / "sub" / "nested"
        mgr = TempManager(temp_dir=nested)
        result = mgr.create_temp_file("test", ".txt")
        assert result.exists() or result.parent.exists()


class TestCreateTempManager:
    def test_returns_instance(self) -> None:
        mgr = create_temp_manager()
        assert isinstance(mgr, TempManager)

    def test_singleton_behavior(self) -> None:
        mgr1 = create_temp_manager()
        mgr2 = create_temp_manager()
        assert mgr1 is mgr2
