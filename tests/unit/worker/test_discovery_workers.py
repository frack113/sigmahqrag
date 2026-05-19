"""Tests for discovery workers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.back.worker.workers.github_discovery_worker import GithubDiscoveryWorker
from src.back.worker.workers.local_discovery_worker import LocalDiscoveryWorker
from src.back.worker.workers.sigmaref_discovery_worker import SigmaRefDiscoveryWorker


class TestSigmaRefDiscoveryWorker:
    @pytest.mark.asyncio
    async def test_process_calls_download_references(self, mock_db: MagicMock) -> None:
        task = {
            "task_id": "sr-disc-001",
            "task_type": "sigmaref_discovery",
            "collection_name": "sigmaref",
            "rules_dir": "data/rules",
            "output_dir": "data/documents/sigmaref",
        }

        summary = {"total_rules": 10, "total_refs": 5, "downloaded": 3, "skipped": 2, "failed": 0}

        with patch(
            "src.back.worker.workers.sigmaref_discovery_worker.download_references",
            return_value=summary,
        ) as mock_download:
            worker = SigmaRefDiscoveryWorker(mock_db)
            await worker.process(task)

        mock_download.assert_called_once_with(
            rules_dir="data/rules",
            output_dir="data/documents/sigmaref",
            supported_types={"markdown"},
        )

    @pytest.mark.asyncio
    async def test_process_reports_completed(self, mock_db: MagicMock) -> None:
        task = {
            "task_id": "sr-disc-002",
            "task_type": "sigmaref_discovery",
            "collection_name": "sigmaref",
        }

        summary = {"total_rules": 5, "total_refs": 3, "downloaded": 2, "skipped": 1, "failed": 0}

        with patch(
            "src.back.worker.workers.sigmaref_discovery_worker.download_references",
            return_value=summary,
        ):
            worker = SigmaRefDiscoveryWorker(mock_db)
            await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"
        assert final_call.kwargs["source_type"] == "sigmaref_discovery"
        assert final_call.kwargs["processed"] == 2
        assert final_call.kwargs["skipped"] == 1

    @pytest.mark.asyncio
    async def test_process_reports_failed_downloads(self, mock_db: MagicMock) -> None:
        task = {
            "task_id": "sr-disc-003",
            "task_type": "sigmaref_discovery",
            "collection_name": "sigmaref",
        }

        summary = {"total_rules": 5, "total_refs": 3, "downloaded": 1, "skipped": 1, "failed": 1}

        with patch(
            "src.back.worker.workers.sigmaref_discovery_worker.download_references",
            return_value=summary,
        ):
            worker = SigmaRefDiscoveryWorker(mock_db)
            await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"
        assert "1 downloads failed" in final_call.kwargs["errors"]

    @pytest.mark.asyncio
    async def test_process_sets_running_status(self, mock_db: MagicMock) -> None:
        task = {
            "task_id": "sr-disc-004",
            "task_type": "sigmaref_discovery",
            "collection_name": "sigmaref",
        }

        with patch(
            "src.back.worker.workers.sigmaref_discovery_worker.download_references",
            return_value={
                "total_rules": 0,
                "total_refs": 0,
                "downloaded": 0,
                "skipped": 0,
                "failed": 0,
            },
        ):
            worker = SigmaRefDiscoveryWorker(mock_db)
            await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        first_call = calls[0]
        assert first_call.kwargs["status"] == "running"
        assert first_call.kwargs["current_file"] == "scanning rules..."


class TestGithubDiscoveryWorker:
    @pytest.mark.asyncio
    async def test_process_completes_if_no_repos(self, mock_db: MagicMock) -> None:
        mock_db.get_repos_with_selected_dirs.return_value = []

        task = {
            "task_id": "gh-disc-001",
            "task_type": "github_discovery",
            "collection_name": "all",
        }

        worker = GithubDiscoveryWorker(mock_db)
        await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"
        assert final_call.kwargs["total"] == 0

    @pytest.mark.asyncio
    async def test_process_scans_multiple_repos(self, mock_db: MagicMock, tmp_path: Path) -> None:
        repo1 = tmp_path / "test-org" / "test-repo" / "rules"
        repo1.mkdir(parents=True)
        (repo1 / "rule1.md").write_text("# Rule 1")
        (repo1 / "rule2.md").write_text("# Rule 2")

        repo2 = tmp_path / "other-org" / "other-repo" / "docs"
        repo2.mkdir(parents=True)
        (repo2 / "doc1.md").write_text("# Doc 1")

        mock_db.get_repos_with_selected_dirs.return_value = [
            "test-org/test-repo",
            "other-org/other-repo",
        ]
        mock_db.get_selected_dirs.return_value = []

        task = {
            "task_id": "gh-disc-003",
            "task_type": "github_discovery",
            "collection_name": "all",
        }

        worker = GithubDiscoveryWorker(mock_db)
        worker.github_base_dir = str(tmp_path)
        await worker.process(task)

        assert mock_db.upsert_doc_registry.call_count == 3
        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"
        assert final_call.kwargs["processed"] == 3
        assert final_call.kwargs["collection_name"] == "all"

    @pytest.mark.asyncio
    async def test_process_respects_selected_dirs(self, mock_db: MagicMock, tmp_path: Path) -> None:
        repo_dir = tmp_path / "test-org" / "test-repo"
        rules_dir = repo_dir / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "rule1.md").write_text("# Rule 1")
        specs_dir = repo_dir / "specs"
        specs_dir.mkdir(parents=True)
        (specs_dir / "spec1.md").write_text("# Spec 1")

        mock_db.get_repos_with_selected_dirs.return_value = ["test-org/test-repo"]
        mock_db.get_selected_dirs.return_value = ["rules"]

        task = {
            "task_id": "gh-disc-004",
            "task_type": "github_discovery",
            "collection_name": "all",
        }

        worker = GithubDiscoveryWorker(mock_db)
        worker.github_base_dir = str(tmp_path)
        await worker.process(task)

        assert mock_db.upsert_doc_registry.call_count == 1

    @pytest.mark.asyncio
    async def test_process_skips_missing_repos(self, mock_db: MagicMock, tmp_path: Path) -> None:
        repo_dir = tmp_path / "test-org" / "test-repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "file.md").write_text("# File")

        mock_db.get_repos_with_selected_dirs.return_value = [
            "test-org/test-repo",
            "missing-org/missing-repo",
        ]
        mock_db.get_selected_dirs.return_value = []

        task = {
            "task_id": "gh-disc-005",
            "task_type": "github_discovery",
            "collection_name": "all",
        }

        worker = GithubDiscoveryWorker(mock_db)
        worker.github_base_dir = str(tmp_path)
        await worker.process(task)

        assert mock_db.upsert_doc_registry.call_count == 1
        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"

    @pytest.mark.asyncio
    async def test_process_sets_embed_status(self, mock_db: MagicMock, tmp_path: Path) -> None:
        repo_dir = tmp_path / "test-org" / "test-repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "file.md").write_text("# File")

        mock_db.get_repos_with_selected_dirs.return_value = ["test-org/test-repo"]
        mock_db.get_selected_dirs.return_value = []

        task = {
            "task_id": "gh-disc-006",
            "task_type": "github_discovery",
            "collection_name": "all",
        }

        worker = GithubDiscoveryWorker(mock_db)
        worker.github_base_dir = str(tmp_path)
        await worker.process(task)

        assert mock_db.upsert_doc_registry.call_count >= 1
        call_args = mock_db.upsert_doc_registry.call_args_list[0][0][0]
        assert call_args["embed_status"] == "discovered"


class TestLocalDiscoveryWorker:
    @pytest.mark.asyncio
    async def test_process_completes_if_path_missing(self, mock_db: MagicMock) -> None:
        task = {
            "task_id": "local-disc-001",
            "task_type": "local_discovery",
            "collection_name": "local",
            "base_path": "/nonexistent/path",
        }

        worker = LocalDiscoveryWorker(mock_db)
        await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"
        assert final_call.kwargs["total"] == 0

    @pytest.mark.asyncio
    async def test_process_scans_local_directory(self, mock_db: MagicMock, tmp_path: Path) -> None:
        local_dir = tmp_path / "local_docs"
        local_dir.mkdir()
        (local_dir / "doc1.md").write_text("# Doc 1")
        (local_dir / "doc2.md").write_text("# Doc 2")

        task = {
            "task_id": "local-disc-002",
            "task_type": "local_discovery",
            "collection_name": "local",
            "base_path": str(local_dir),
        }

        worker = LocalDiscoveryWorker(mock_db)
        await worker.process(task)

        assert mock_db.upsert_doc_registry.call_count == 2
        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"
        assert final_call.kwargs["processed"] == 2

    @pytest.mark.asyncio
    async def test_process_uses_default_path(self, mock_db: MagicMock) -> None:
        task = {
            "task_id": "local-disc-003",
            "task_type": "local_discovery",
            "collection_name": "local",
        }

        worker = LocalDiscoveryWorker(mock_db)
        await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"
        assert final_call.kwargs["current_file"] == "path not found"

    @pytest.mark.asyncio
    async def test_process_reports_source_type(self, mock_db: MagicMock, tmp_path: Path) -> None:
        local_dir = tmp_path / "local_docs"
        local_dir.mkdir()
        (local_dir / "doc1.md").write_text("# Doc 1")

        task = {
            "task_id": "local-disc-004",
            "task_type": "local_discovery",
            "collection_name": "local",
            "base_path": str(local_dir),
        }

        worker = LocalDiscoveryWorker(mock_db)
        await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        assert all(c.kwargs["source_type"] == "local_discovery" for c in calls)
