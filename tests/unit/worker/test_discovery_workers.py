"""Tests for discovery workers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.worker.workers.generic_discovery_worker import GenericDiscoveryWorker, SourceType
from src.worker.workers.sigmaref_worker import SigmaRefProcessor


class TestSigmaRefProcessor:
    def test_process_calls_process_sigma_refs(self, mock_db: MagicMock) -> None:
        task = {
            "task_id": "sr-disc-001",
            "task_type": "sigmaref_discovery",
            "collection_name": "sigmaref",
            "rules_dir": "data/github",
            "output_dir": "data/documents/sigmaref",
            "selected_dirs": [""],
        }

        summary = {"total_rules": 10, "total_refs": 5, "downloaded": 3, "skipped": 2, "failed": 0}

        with patch(
            "src.worker.workers.sigmaref_worker.process_sigma_refs",
            return_value=summary,
        ) as mock_process:
            dispatcher = MagicMock()
            dispatcher.update_worker_state = MagicMock()
            worker = SigmaRefProcessor(mock_db, dispatcher)
            worker.process(task)

        mock_process.assert_called_once()
        call_kwargs = mock_process.call_args[1]
        assert call_kwargs["db"] == mock_db
        assert call_kwargs["output_dir"] == "data/documents/sigmaref"

    def test_process_propagates_errors(self, mock_db: MagicMock) -> None:
        task = {
            "task_id": "sr-disc-003",
            "task_type": "sigmaref_discovery",
            "collection_name": "sigmaref",
            "selected_dirs": [""],
        }

        with patch(
            "src.worker.workers.sigmaref_worker.process_sigma_refs",
            side_effect=RuntimeError("download failed"),
        ):
            dispatcher = MagicMock()
            dispatcher.update_worker_state = MagicMock()
            worker = SigmaRefProcessor(mock_db, dispatcher)
            with pytest.raises(RuntimeError, match="download failed"):
                worker.process(task)


class TestGithubDiscoveryWorker:
    def test_process_completes_if_no_repos(self, mock_db: MagicMock) -> None:
        mock_db.get_repos_with_selected_dirs.return_value = []

        task = {
            "task_id": "gh-disc-001",
            "task_type": "github_discovery",
            "collection_name": "all",
        }

        worker = GenericDiscoveryWorker(
            db=mock_db, source_type=SourceType.GITHUB, base_dir=Path("/tmp")
        )
        worker.process(task)

    def test_process_scans_multiple_repos(self, mock_db: MagicMock, tmp_path: Path) -> None:
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
            "github_base_dir": str(tmp_path),
        }

        worker = GenericDiscoveryWorker(
            db=mock_db, source_type=SourceType.GITHUB, base_dir=tmp_path
        )
        worker.process(task)

        mock_db.batch_upsert_doc_registry.assert_called_once()
        entries = mock_db.batch_upsert_doc_registry.call_args[0][0]
        assert len(entries) == 3

    def test_process_respects_selected_dirs(self, mock_db: MagicMock, tmp_path: Path) -> None:
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
            "github_base_dir": str(tmp_path),
        }

        worker = GenericDiscoveryWorker(
            db=mock_db, source_type=SourceType.GITHUB, base_dir=tmp_path
        )
        worker.process(task)

        mock_db.batch_upsert_doc_registry.assert_called_once()
        entries = mock_db.batch_upsert_doc_registry.call_args[0][0]
        assert len(entries) == 1

    def test_process_selected_dirs_not_prefix_match(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        """Selected dir 'rules' must not match 'rulesets' (prefix bug)."""
        repo_dir = tmp_path / "test-org" / "test-repo"
        rules_dir = repo_dir / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "rule1.md").write_text("# Rule 1")
        rulesets_dir = repo_dir / "rulesets"
        rulesets_dir.mkdir(parents=True)
        (rulesets_dir / "ruleset1.md").write_text("# Ruleset 1")

        mock_db.get_repos_with_selected_dirs.return_value = ["test-org/test-repo"]
        mock_db.get_selected_dirs.return_value = ["rules"]

        task = {
            "task_id": "gh-disc-prefix",
            "task_type": "github_discovery",
            "collection_name": "all",
            "github_base_dir": str(tmp_path),
        }

        worker = GenericDiscoveryWorker(
            db=mock_db, source_type=SourceType.GITHUB, base_dir=tmp_path
        )
        worker.process(task)

        mock_db.batch_upsert_doc_registry.assert_called_once()
        entries = mock_db.batch_upsert_doc_registry.call_args[0][0]
        assert len(entries) == 1
        assert entries[0]["file_name"] == "rules/rule1.md"

    def test_process_skips_missing_repos(self, mock_db: MagicMock, tmp_path: Path) -> None:
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
            "github_base_dir": str(tmp_path),
        }

        worker = GenericDiscoveryWorker(
            db=mock_db, source_type=SourceType.GITHUB, base_dir=tmp_path
        )
        worker.process(task)

        mock_db.batch_upsert_doc_registry.assert_called_once()
        entries = mock_db.batch_upsert_doc_registry.call_args[0][0]
        assert len(entries) == 1

    def test_process_sets_embed_status(self, mock_db: MagicMock, tmp_path: Path) -> None:
        repo_dir = tmp_path / "test-org" / "test-repo"
        repo_dir.mkdir(parents=True)
        (repo_dir / "file.md").write_text("# File")

        mock_db.get_repos_with_selected_dirs.return_value = ["test-org/test-repo"]
        mock_db.get_selected_dirs.return_value = []

        task = {
            "task_id": "gh-disc-006",
            "task_type": "github_discovery",
            "collection_name": "all",
            "github_base_dir": str(tmp_path),
        }

        worker = GenericDiscoveryWorker(
            db=mock_db, source_type=SourceType.GITHUB, base_dir=tmp_path
        )
        worker.process(task)

        mock_db.batch_upsert_doc_registry.assert_called_once()
        entries = mock_db.batch_upsert_doc_registry.call_args[0][0]
        assert entries[0]["embed_status"] == "discovery"


class TestLocalDiscoveryWorker:
    def test_process_completes_if_path_missing(self, mock_db: MagicMock) -> None:
        task = {
            "task_id": "local-disc-001",
            "task_type": "local_discovery",
            "collection_name": "local",
            "base_path": "/nonexistent/path",
        }

        worker = GenericDiscoveryWorker(
            db=mock_db, source_type=SourceType.LOCAL, base_dir=Path("/nonexistent")
        )
        worker.process(task)

    def test_process_scans_local_directory(self, mock_db: MagicMock, tmp_path: Path) -> None:
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

        worker = GenericDiscoveryWorker(db=mock_db, source_type=SourceType.LOCAL, base_dir=tmp_path)
        worker.process(task)

        mock_db.batch_upsert_doc_registry.assert_called_once()
        entries = mock_db.batch_upsert_doc_registry.call_args[0][0]
        assert len(entries) == 2

    def test_process_uses_default_path(self, mock_db: MagicMock) -> None:
        task = {
            "task_id": "local-disc-003",
            "task_type": "local_discovery",
            "collection_name": "local",
        }

        worker = GenericDiscoveryWorker(
            db=mock_db, source_type=SourceType.LOCAL, base_dir=Path("/tmp")
        )
        worker.process(task)

    def test_process_reports_source_type(self, mock_db: MagicMock, tmp_path: Path) -> None:
        local_dir = tmp_path / "local_docs"
        local_dir.mkdir()
        (local_dir / "doc1.md").write_text("# Doc 1")

        task = {
            "task_id": "local-disc-004",
            "task_type": "local_discovery",
            "collection_name": "local",
            "base_path": str(local_dir),
        }

        worker = GenericDiscoveryWorker(db=mock_db, source_type=SourceType.LOCAL, base_dir=tmp_path)
        worker.process(task)

        mock_db.batch_upsert_doc_registry.assert_called_once()
        entries = mock_db.batch_upsert_doc_registry.call_args[0][0]
        assert all(e["org"] == "local" for e in entries)
