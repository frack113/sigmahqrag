"""Advanced tests for GithubDiscoveryWorker — error path and edge case coverage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.worker.workers.github_discovery_worker import GithubDiscoveryWorker


class TestGithubDiscoveryWorkerAdvanced:
    def test_build_urls_handles_metadata_exception(self, mock_db: MagicMock) -> None:
        mock_db.get_git_metadata.side_effect = RuntimeError("db error")
        worker = GithubDiscoveryWorker(mock_db)
        original, normalized = worker._build_urls("org", "repo", "path/file.md")
        assert "main" in original
        assert normalized.startswith("https://raw.githubusercontent.com")

    def test_process_file_handles_relativize_error(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        worker = GithubDiscoveryWorker(mock_db)
        file_path = tmp_path / "outside.md"
        file_path.write_text("test")
        base_path = tmp_path / "repo"
        result = worker._prepare_entry(file_path, base_path, "org", "repo")
        assert result is None

    def test_process_file_handles_read_bytes_error(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        repo_dir = tmp_path / "org" / "repo"
        repo_dir.mkdir(parents=True)
        file_path = repo_dir / "file.md"
        file_path.write_text("test")

        mock_db.get_git_metadata.return_value = {"branch": "main"}

        worker = GithubDiscoveryWorker(mock_db)
        with patch.object(worker, "_compute_sha256", return_value=("", 0)):
            result = worker._prepare_entry(file_path, repo_dir, "org", "repo")
            assert result is not None
            assert result["content_sha256"] == ""
            assert result["file_size"] == 0

    def test_process_file_handles_identify_error(self, mock_db: MagicMock, tmp_path: Path) -> None:
        repo_dir = tmp_path / "org" / "repo"
        repo_dir.mkdir(parents=True)
        file_path = repo_dir / "file.md"
        file_path.write_text("test")

        mock_db.get_git_metadata.return_value = {"branch": "main"}

        worker = GithubDiscoveryWorker(mock_db)
        with patch(
            "src.worker.workers.discovery_base.identify",
            side_effect=ValueError("unknown type"),
        ):
            result = worker._prepare_entry(file_path, repo_dir, "org", "repo")
            assert result is not None
            assert result["content_type"] == "unknown"

    def test_process_handles_invalid_repo_key(self, mock_db: MagicMock, tmp_path: Path) -> None:
        mock_db.get_repos_with_selected_dirs.return_value = ["invalid"]
        task = {
            "task_id": "gh-adv-001",
            "github_base_dir": str(tmp_path),
        }
        worker = GithubDiscoveryWorker(mock_db)
        worker.process(task)

    def test_process_handles_selected_dirs_db_error(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        repo_dir = tmp_path / "org" / "repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "file.md").write_text("test")

        mock_db.get_repos_with_selected_dirs.return_value = ["org/repo"]
        mock_db.get_selected_dirs.side_effect = RuntimeError("db error")

        task = {
            "task_id": "gh-adv-002",
            "github_base_dir": str(tmp_path),
        }
        worker = GithubDiscoveryWorker(mock_db)
        worker.process(task)
        assert mock_db.batch_upsert_doc_registry.call_count >= 1

    def test_process_reports_progress(self, mock_db: MagicMock, tmp_path: Path) -> None:
        repo_dir = tmp_path / "org" / "repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "file.md").write_text("test")
        (repo_dir / "file2.md").write_text("test2")

        mock_db.get_repos_with_selected_dirs.return_value = ["org/repo"]
        mock_db.get_selected_dirs.return_value = []

        mock_dispatcher = MagicMock()
        worker = GithubDiscoveryWorker(mock_db, mock_dispatcher)

        task = {
            "task_id": "gh-adv-003",
            "github_base_dir": str(tmp_path),
        }
        worker.process(task)
        mock_dispatcher.update_worker_state.assert_called()

    def test_process_no_repos_reports_progress(self, mock_db: MagicMock) -> None:
        mock_db.get_repos_with_selected_dirs.return_value = []
        mock_dispatcher = MagicMock()
        worker = GithubDiscoveryWorker(mock_db, mock_dispatcher)

        task = {"task_id": "gh-adv-004"}
        worker.process(task)
        mock_dispatcher.update_worker_state.assert_called()

    def test_process_file_exception_in_loop(self, mock_db: MagicMock, tmp_path: Path) -> None:
        repo_dir = tmp_path / "org" / "repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "file.md").write_text("test")

        mock_db.get_repos_with_selected_dirs.return_value = ["org/repo"]
        mock_db.get_selected_dirs.return_value = []

        worker = GithubDiscoveryWorker(mock_db)
        bad_mock = MagicMock()
        bad_mock.relative_to.side_effect = RuntimeError("unexpected")
        with patch.object(Path, "relative_to", side_effect=RuntimeError("unexpected")):
            worker.process(
                {
                    "task_id": "gh-adv-005",
                    "github_base_dir": str(tmp_path),
                }
            )

    def test_fatal_exception_is_raised(self, mock_db: MagicMock) -> None:
        mock_db.get_repos_with_selected_dirs.side_effect = RuntimeError("fatal")
        worker = GithubDiscoveryWorker(mock_db)
        with pytest.raises(RuntimeError):
            worker.process({"task_id": "gh-adv-006"})

    def test_process_skipped_count_on_false_return(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        repo_dir = tmp_path / "org" / "repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "file.md").write_text("test")

        mock_db.get_repos_with_selected_dirs.return_value = ["org/repo"]
        mock_db.get_selected_dirs.return_value = []

        worker = GithubDiscoveryWorker(mock_db)
        with patch.object(worker, "_prepare_entry", return_value=None):
            worker.process(
                {
                    "task_id": "gh-adv-007",
                    "github_base_dir": str(tmp_path),
                }
            )
