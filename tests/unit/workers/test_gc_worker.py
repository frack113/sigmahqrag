"""Tests for DocGCWorker and orphaned sigmaref file cleaning."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.workers.document.gc_worker import DocGCWorker, _is_orphan_candidate

_VALID_HASH = "ab" * 32  # 64-char hex
_ORPHAN_HASH = "ef" * 32


class TestIsOrphanCandidate:
    def test_accepts_unknown_hash(self) -> None:
        assert _is_orphan_candidate(_VALID_HASH, set()) is True

    def test_rejects_known_hash(self) -> None:
        assert _is_orphan_candidate(_VALID_HASH, {_VALID_HASH}) is False

    def test_rejects_short_stem(self) -> None:
        assert _is_orphan_candidate("too-short", set()) is False

    def test_rejects_non_hex_stem(self) -> None:
        assert _is_orphan_candidate("z" + _VALID_HASH[1:], set()) is False

    def test_rejects_dotfile(self) -> None:
        assert _is_orphan_candidate(".keep", set()) is False


def _make_db(known_hashes: set[str] | None = None) -> MagicMock:
    db = MagicMock()
    lock = MagicMock()
    db._lock = lock
    db._writer_conn.execute.return_value.fetchall.return_value = [
        (h,) for h in (known_hashes or {_VALID_HASH})
    ]
    return db


def _make_worker(known_hashes: set[str] | None = None) -> DocGCWorker:
    """Build a DocGCWorker with a mocked DB that returns *known_hashes*."""
    db = _make_db(known_hashes)
    worker = DocGCWorker(db=db)
    worker.dispatcher = MagicMock()
    return worker


def _touch(d: Path, name: str) -> Path:
    p = d / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("test")
    return p


class TestGcOrphanedSigmarefFiles:
    def test_removes_orphan_in_flat_layout(self, tmp_path: Path) -> None:
        base = tmp_path / "sigmaref"
        base.mkdir()
        _touch(base, _VALID_HASH + ".md")  # known
        orphan = _touch(base, _ORPHAN_HASH + ".md")  # orphan

        worker = _make_worker()
        with patch("src.workers.document.gc_worker.get_config") as mock_cfg:
            mock_cfg.return_value.sigmaref_documents_path = str(base)
            result = worker._gc_orphaned_sigmaref_files()

        assert result == 1
        assert not orphan.exists()
        known_file = _VALID_HASH + ".md"
        assert (base / known_file).exists()

    def test_removes_orphan_in_subdir(self, tmp_path: Path) -> None:
        base = tmp_path / "sigmaref"
        base.mkdir()
        orphan = _touch(base / "markdown", _ORPHAN_HASH + ".md")

        worker = _make_worker()
        with patch("src.workers.document.gc_worker.get_config") as mock_cfg:
            mock_cfg.return_value.sigmaref_documents_path = str(base)
            result = worker._gc_orphaned_sigmaref_files()

        assert result == 1
        assert not orphan.exists()

    def test_skips_known_file(self, tmp_path: Path) -> None:
        base = tmp_path / "sigmaref"
        base.mkdir()
        known = _touch(base, _VALID_HASH + ".md")

        worker = _make_worker()
        with patch("src.workers.document.gc_worker.get_config") as mock_cfg:
            mock_cfg.return_value.sigmaref_documents_path = str(base)
            result = worker._gc_orphaned_sigmaref_files()

        assert result == 0
        assert known.exists()

    def test_skips_dotfiles(self, tmp_path: Path) -> None:
        base = tmp_path / "sigmaref"
        base.mkdir()
        dotfile = _touch(base, ".keep")

        worker = _make_worker(known_hashes=set())
        with patch("src.workers.document.gc_worker.get_config") as mock_cfg:
            mock_cfg.return_value.sigmaref_documents_path = str(base)
            result = worker._gc_orphaned_sigmaref_files()

        assert result == 0
        assert dotfile.exists()

    def test_removes_empty_subdir(self, tmp_path: Path) -> None:
        base = tmp_path / "sigmaref"
        base.mkdir()
        sub = base / "pdf"
        sub.mkdir()

        worker = _make_worker(known_hashes=set())
        with patch("src.workers.document.gc_worker.get_config") as mock_cfg:
            mock_cfg.return_value.sigmaref_documents_path = str(base)
            worker._gc_orphaned_sigmaref_files()

        assert not sub.exists()

    def test_files_go_to_trash(self, tmp_path: Path) -> None:
        base = tmp_path / "sigmaref"
        base.mkdir()
        orphan = _touch(base, _ORPHAN_HASH + ".md")

        worker = _make_worker(known_hashes=set())
        with patch("src.workers.document.gc_worker.get_config") as mock_cfg:
            mock_cfg.return_value.sigmaref_documents_path = str(base)
            worker._gc_orphaned_sigmaref_files()

        assert (base / ".trash" / (_ORPHAN_HASH + ".md")).exists()
        assert not orphan.exists()

    def test_noop_when_base_missing(self) -> None:
        worker = _make_worker()
        with patch("src.workers.document.gc_worker.get_config") as mock_cfg:
            mock_cfg.return_value.sigmaref_documents_path = "/nonexistent"
            result = worker._gc_orphaned_sigmaref_files()

        assert result == 0

    def test_db_error_returns_zero(self, tmp_path: Path) -> None:
        base = tmp_path / "sigmaref"
        base.mkdir()

        db = _make_db(known_hashes=set())
        db._writer_conn.execute.side_effect = RuntimeError("db down")
        worker = DocGCWorker(db=db)

        with patch("src.workers.document.gc_worker.get_config") as mock_cfg:
            mock_cfg.return_value.sigmaref_documents_path = str(base)
            result = worker._gc_orphaned_sigmaref_files()

        assert result == 0
