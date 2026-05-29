"""Tests for LocalRepoSyncWorker."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.worker.workers.local_repo_sync_worker import LocalRepoSyncWorker


class TestLocalRepoSyncWorker:
    def test_syncs_new_repos(self, mock_db: MagicMock) -> None:
        mock_dispatcher = MagicMock()
        worker = LocalRepoSyncWorker(mock_db, mock_dispatcher)

        with patch("src.worker.workers.local_repo_sync_worker.list_repos") as mock_list:
            mock_list.return_value = [
                {"org": "test-org", "name": "repo-a", "remote_url": "https://example.com/a.git"},
            ]
            with patch("src.worker.workers.local_repo_sync_worker.get_metadata", return_value=None):
                with patch("src.worker.workers.local_repo_sync_worker.save_metadata") as mock_save:
                    worker.process({"task_id": "lrs-1"})
                    mock_save.assert_called_once()
                    args = mock_save.call_args[0]
                    assert args[0] == "test-org"
                    assert args[1] == "repo-a"

    def test_skips_existing_repos(self, mock_db: MagicMock) -> None:
        mock_dispatcher = MagicMock()
        worker = LocalRepoSyncWorker(mock_db, mock_dispatcher)

        with (
            patch("src.worker.workers.local_repo_sync_worker.list_repos") as mock_list,
            patch(
                "src.worker.workers.local_repo_sync_worker.get_metadata",
                return_value={"remote_head": "abc123"},
            ),
            patch("src.worker.workers.local_repo_sync_worker.save_metadata") as mock_save,
        ):
            mock_list.return_value = [
                {"org": "test-org", "name": "repo-a", "remote_head": "abc123"},
            ]
            worker.process({"task_id": "lrs-2"})
            mock_save.assert_not_called()

    def test_updates_missing_remote_head(self, mock_db: MagicMock) -> None:
        mock_dispatcher = MagicMock()
        worker = LocalRepoSyncWorker(mock_db, mock_dispatcher)

        with (
            patch("src.worker.workers.local_repo_sync_worker.list_repos") as mock_list,
            patch(
                "src.worker.workers.local_repo_sync_worker.get_metadata",
                return_value={"status": "synced"},
            ),
            patch("src.worker.workers.local_repo_sync_worker.save_metadata") as mock_save,
        ):
            mock_list.return_value = [
                {"org": "test-org", "name": "repo-a", "remote_head": "def456"},
            ]
            worker.process({"task_id": "lrs-3"})
            mock_save.assert_called_once()
            saved = mock_save.call_args[0][2]
            assert saved["remote_head"] == "def456"

    def test_handles_dispatcher_state(self, mock_db: MagicMock) -> None:
        mock_dispatcher = MagicMock()
        worker = LocalRepoSyncWorker(mock_db, mock_dispatcher)

        with patch("src.worker.workers.local_repo_sync_worker.list_repos", return_value=[]):
            worker.process({"task_id": "lrs-4"})
            assert mock_dispatcher.update_worker_state.call_count >= 2
