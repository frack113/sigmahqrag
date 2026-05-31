"""Advanced tests for GenericEmbeddingWorker — remaining coverage lines."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.worker.workers.generic_embedding_worker import GenericEmbeddingWorker


class TestGenericEmbeddingWorkerAdvanced:
    def test_get_entries_skips_missing_url_hash(self, mock_db: MagicMock) -> None:
        mock_db.get_pending_entries.return_value = [
            {"original_url": "https://example.com/doc"},
        ]
        worker = GenericEmbeddingWorker(mock_db, MagicMock())
        entries = worker._get_entries({"task_id": "t1", "org": "sigmaref"})
        assert len(entries) == 0

    def test_resolve_file_path_returns_none_when_no_hash_or_name(self, mock_db: MagicMock) -> None:
        worker = GenericEmbeddingWorker(mock_db, MagicMock())
        worker._task = {}
        result = worker._resolve_file_path({})
        assert result is None

    def test_resolve_file_path_skips_when_candidate_equals_registry(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        worker = GenericEmbeddingWorker(mock_db, MagicMock())
        worker._task = {"registry_path": str(tmp_path)}
        (tmp_path / "test-name.md").write_text("# Doc")
        result = worker._resolve_file_path({"file_name": "test-name.md", "org": "sigmaref"})
        assert result is not None
        assert result.name == "test-name.md"

    def test_resolve_file_path_skips_registry_path_candidate(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        worker = GenericEmbeddingWorker(mock_db, MagicMock())
        worker._task = {"registry_path": str(tmp_path)}
        (tmp_path / "somehash.md").write_text("# found")
        result = worker._resolve_file_path({"hash": "somehash", "file_name": "", "org": "sigmaref"})
        assert result is not None
        assert result.name == "somehash.md"
