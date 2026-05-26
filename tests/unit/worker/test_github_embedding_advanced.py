"""Advanced tests for GithubEmbeddingWorker — remaining coverage lines."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.worker.workers.github_embedding_worker import GithubEmbeddingWorker


class TestGithubEmbeddingWorkerAdvanced:
    def test_get_entries_invalid_collection_format(self, mock_db: MagicMock) -> None:
        task = {"task_id": "adv-1", "collection_name": "too/many/slashes"}
        worker = GithubEmbeddingWorker(mock_db, MagicMock())
        with pytest.raises(ValueError, match="Invalid collection_name format"):
            worker._get_entries(task)

    def test_get_entries_specific_repo_exists(self, mock_db: MagicMock, tmp_path: Path) -> None:
        repo_dir = tmp_path / "org" / "repo"
        repo_dir.mkdir(parents=True)
        mock_db.get_pending_sigma_ref.return_value = [{"file_name": "doc.md"}]

        task = {"task_id": "adv-2", "collection_name": "org/repo"}
        with patch("src.worker.workers.github_embedding_worker.get_config") as mock_cfg:
            mock_cfg.return_value.paths_github_dir = str(tmp_path)
            worker = GithubEmbeddingWorker(mock_db, MagicMock())
            entries = worker._get_entries(task)
            assert len(entries) == 1
            mock_db.get_pending_sigma_ref.assert_called_with("org", "repo")

    def test_resolve_file_path_returns_none_when_missing_fields(self, mock_db: MagicMock) -> None:
        worker = GithubEmbeddingWorker(mock_db, MagicMock())
        assert worker._resolve_file_path({}) is None
        assert worker._resolve_file_path({"org": "o"}) is None
        assert worker._resolve_file_path({"org": "o", "repo": "r"}) is None
