"""Tests for DataDirManager."""

from pathlib import Path

import src.application.system.datadir


class TestOfficialDirs:
    def test_returns_expected_count(self, tmp_path: Path) -> None:
        dirs = src.application.system.datadir.DataDirManager.official_dirs(str(tmp_path))
        assert len(dirs) == 15  # 13 leaves + documents + models parents

    def test_base_is_resolved(self, tmp_path: Path) -> None:
        dirs = src.application.system.datadir.DataDirManager.official_dirs(str(tmp_path))
        first = next(d for d in dirs if d.relative == "bin")
        assert first.absolute == tmp_path / "bin"

    def test_flattens_nested_to_leaves(self, tmp_path: Path) -> None:
        dirs = src.application.system.datadir.DataDirManager.official_dirs(str(tmp_path))
        names = [d.relative for d in dirs]
        # documents and models should be present alongside their children
        assert "documents" in names
        assert "documents/local" in names
        assert "models" in names
        assert "models/llm" in names


class TestCreateMissing:
    def test_creates_single_missing_dir(self, tmp_path: Path) -> None:
        mgr = src.application.system.datadir.DataDirManager(tmp_path)
        created = mgr.create_missing()
        assert any("bin" in c for c in created)
        assert (tmp_path / "bin").exists()

    def test_idempotent(self, tmp_path: Path) -> None:
        mgr = src.application.system.datadir.DataDirManager(tmp_path)
        mgr.create_missing()
        created = mgr.create_missing()
        assert created == []

    def test_returns_absolute_paths(self, tmp_path: Path) -> None:
        mgr = src.application.system.datadir.DataDirManager(tmp_path)
        created = mgr.create_missing()
        for c in created:
            assert Path(c).is_absolute()


class TestEnsureAll:
    def test_creates_all(self, tmp_path: Path) -> None:
        mgr = src.application.system.datadir.DataDirManager(tmp_path)
        mgr.ensure_all()
        dirs = mgr.official_dirs(tmp_path)
        for d in dirs:
            assert d.absolute.exists()


class TestClean:
    def test_removes_non_official(self, tmp_path: Path) -> None:
        mgr = src.application.system.datadir.DataDirManager(tmp_path)
        mgr.create_missing()
        # add trash
        (tmp_path / "tmp").mkdir()
        (tmp_path / "rag_cache").mkdir()
        (tmp_path / "mitre").mkdir()
        removed = mgr.clean()
        removed_names = [Path(r).name for r in removed]
        assert "tmp" in removed_names
        assert "rag_cache" in removed_names
        assert "mitre" in removed_names

    def test_keeps_official(self, tmp_path: Path) -> None:
        mgr = src.application.system.datadir.DataDirManager(tmp_path)
        mgr.create_missing()
        removed = mgr.clean()
        assert removed == []

    def test_removes_stray_files(self, tmp_path: Path) -> None:
        mgr = src.application.system.datadir.DataDirManager(tmp_path)
        mgr.create_missing()
        (tmp_path / "stray.txt").touch()
        removed = mgr.clean()
        assert any("stray.txt" in r for r in removed)

    def test_handles_missing_base(self) -> None:
        mgr = src.application.system.datadir.DataDirManager("/tmp/_nonexistent_data_xxx")
        removed = mgr.clean()
        assert removed == []


class TestHardReset:
    def test_removes_and_recreates(self, tmp_path: Path) -> None:
        mgr = src.application.system.datadir.DataDirManager(tmp_path)
        mgr.create_missing()
        (tmp_path / "trash").mkdir()
        (tmp_path / "bin" / "old.exe").touch()
        result = mgr.hard_reset()
        assert result["created"] > 0
        assert result["removed"] >= 0
        assert (tmp_path / "bin").exists()
        assert (tmp_path / "documents").exists()
        assert (tmp_path / "models").exists()
        assert not (tmp_path / "trash").exists()
        dirs = mgr.official_dirs(tmp_path)
        for d in dirs:
            assert d.absolute.exists(), f"{d.relative} not recreated"

    def test_handles_missing_base(self, tmp_path: Path) -> None:
        mgr = src.application.system.datadir.DataDirManager(tmp_path / "fresh")
        result = mgr.hard_reset()
        assert result["created"] > 0

    def test_hard_reset_clears_trash_dirs(self, tmp_path: Path) -> None:
        mgr = src.application.system.datadir.DataDirManager(tmp_path)
        mgr.create_missing()
        (tmp_path / "tmp").mkdir()
        (tmp_path / "pids" / ".secret").touch()
        mgr.hard_reset()
        assert not (tmp_path / "tmp").exists()
        assert (tmp_path / "pids").exists()


class TestStatus:
    def test_all_clean_after_create(self, tmp_path: Path) -> None:
        mgr = src.application.system.datadir.DataDirManager(tmp_path)
        mgr.create_missing()
        s = mgr.status()
        assert all(v == src.application.system.datadir.HealthState.HEALTHY for v in s.values())

    def test_missing_shows_missing(self, tmp_path: Path) -> None:
        mgr = src.application.system.datadir.DataDirManager(tmp_path)
        s = mgr.status()
        assert s["bin"] == src.application.system.datadir.HealthState.MISSING
        assert s["models/llm"] == src.application.system.datadir.HealthState.MISSING

    def test_dirty_detected(self, tmp_path: Path) -> None:
        mgr = src.application.system.datadir.DataDirManager(tmp_path)
        mgr.create_missing()
        # add a dotfile to make bin dirty
        (tmp_path / "bin" / ".trash").touch()
        s = mgr.status()
        assert s["bin"] == src.application.system.datadir.HealthState.DIRTY

    def test_status_detail_returns_all_fields(self, tmp_path: Path) -> None:
        mgr = src.application.system.datadir.DataDirManager(tmp_path)
        mgr.create_missing()
        details = mgr.status_detail()
        assert len(details) > 0
        first = details[0]
        assert first.state == src.application.system.datadir.HealthState.HEALTHY
        assert isinstance(first.has_content, bool)
        assert isinstance(first.is_dirty, bool)
        assert isinstance(first.needs_creation, bool)

    def test_summary_counts(self, tmp_path: Path) -> None:
        mgr = src.application.system.datadir.DataDirManager(tmp_path)
        s = mgr.summary()
        assert s["missing"] > 0
        assert s["healthy"] == 0

        mgr.create_missing()
        s = mgr.summary()
        total = s["healthy"] + s["dirty"] + s["missing"]
        assert total == len(mgr.status_detail())
        assert s["missing"] == 0

    def test_summary_with_dirty(self, tmp_path: Path) -> None:
        mgr = src.application.system.datadir.DataDirManager(tmp_path)
        mgr.create_missing()
        (tmp_path / "temp" / ".trash").touch()
        s = mgr.summary()
        assert s["dirty"] >= 1
