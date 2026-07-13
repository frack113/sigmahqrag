"""Tests for discovery workers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.workers.sigma.discovery_worker import GenericDiscoveryWorker, SourceType
from src.workers.sigma.sigmaref_worker import SigmaRefProcessor


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
            "src.workers.sigma.sigmaref_worker.process_sigma_refs",
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
            "src.workers.sigma.sigmaref_worker.process_sigma_refs",
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


class TestGarbageCollection:
    def test_garbage_collect_clears_stale_entries_across_repos(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        """GC should clean stale entries from ALL repos with active selections, not just the scanned one."""
        repo_a_dir = tmp_path / "org-a" / "repo-a"
        repo_a_dir.mkdir(parents=True)
        (repo_a_dir / "stale.md").write_text("# Stale")

        repo_b_dir = tmp_path / "org-b" / "repo-b"
        repo_b_dir.mkdir(parents=True)
        (repo_b_dir / "active.md").write_text("# Active")

        mock_db.get_repos_with_selected_dirs.return_value = ["org-a/repo-a"]

        stale_hash = "stale-hash-123"
        active_hash = "active-hash-456"

        active_entry = {"url_hash": active_hash, "org": "org-b", "repo": "repo-b"}

        mock_db.get_doc_registry_url_hashes_by_repo.side_effect = lambda org, repo: (
            [stale_hash] if org == "org-a" and repo == "repo-a" else []
        )
        mock_db.get_rule_id_by_url_hash.return_value = "00000000-0000-0000-0000-000000000000"
        mock_db.get_rule_reference_paths.return_value = []

        worker = GenericDiscoveryWorker(
            db=mock_db, source_type=SourceType.GITHUB, base_dir=tmp_path
        )

        # Call GC directly with stale entries from repo A, active entries from repo B
        repo_items = [("org-a", "repo-a"), ("org-b", "repo-b")]
        current_entries = [active_entry]  # Only active entries in current scan

        worker._garbage_collect_github(repo_items, current_entries)

        # Verify: stale entry from repo A was deleted
        mock_db.delete_doc_registry_by_url_hashes.assert_called_once_with([stale_hash])

    def test_garbage_collect_preserves_active_entries(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        """GC should NOT delete entries that are still in the current scan."""
        active_hash = "active-hash-789"
        active_entry = {"url_hash": active_hash, "org": "org", "repo": "repo"}

        mock_db.get_doc_registry_url_hashes_by_repo.return_value = [active_hash]
        mock_db.get_rule_id_by_url_hash.return_value = "00000000-0000-0000-0000-000000000000"
        mock_db.get_rule_reference_paths.return_value = []

        worker = GenericDiscoveryWorker(
            db=mock_db, source_type=SourceType.GITHUB, base_dir=tmp_path
        )

        repo_items = [("org", "repo")]
        current_entries = [active_entry]  # Active entry is in current scan

        worker._garbage_collect_github(repo_items, current_entries)

        # Verify: delete was NOT called (no stale entries)
        mock_db.delete_doc_registry_by_url_hashes.assert_not_called()

    def test_garbage_collect_cleanup_rule_references(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        """GC should delete reference files before deleting doc_registry entries."""
        ref_path = tmp_path / "ref.pdf"
        ref_path.write_bytes(b"fake pdf")

        stale_hash = "stale-ref-hash"
        rule_id = "test-rule-id-123"

        mock_db.get_doc_registry_url_hashes_by_repo.return_value = [stale_hash]
        mock_db.get_rule_id_by_url_hash.return_value = rule_id
        mock_db.get_rule_reference_paths.return_value = [ref_path]

        worker = GenericDiscoveryWorker(
            db=mock_db, source_type=SourceType.GITHUB, base_dir=tmp_path
        )

        repo_items = [("org", "repo")]
        # Pass a dummy active entry so GC doesn't return early
        active_entry = {"url_hash": "active-dummy", "org": "org", "repo": "repo"}
        current_entries: list[dict] = [active_entry]

        worker._garbage_collect_github(repo_items, current_entries)

        # Verify: reference file was deleted
        assert not ref_path.exists()
        # Verify: doc_registry entry was deleted
        mock_db.delete_doc_registry_by_url_hashes.assert_called_once_with([stale_hash])

    def test_garbage_collect_skips_null_rule_id(self, mock_db: MagicMock, tmp_path: Path) -> None:
        """GC should skip entries with null or empty rule_id."""
        stale_hash = "stale-no-rule"

        mock_db.get_doc_registry_url_hashes_by_repo.return_value = [stale_hash]
        mock_db.get_rule_id_by_url_hash.return_value = None  # No rule association

        worker = GenericDiscoveryWorker(
            db=mock_db, source_type=SourceType.GITHUB, base_dir=tmp_path
        )

        repo_items = [("org", "repo")]
        # Pass a dummy active entry so GC doesn't return early
        active_entry = {"url_hash": "active-dummy", "org": "org", "repo": "repo"}
        current_entries: list[dict] = [active_entry]

        worker._garbage_collect_github(repo_items, current_entries)

        # Verify: no cleanup attempted (rule_id is None)
        mock_db.get_rule_reference_paths.assert_not_called()
        mock_db.delete_doc_registry_by_url_hashes.assert_called_once_with([stale_hash])

    def test_garbage_collect_handles_missing_files(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        """GC should not fail if reference files are already missing."""
        ref_path = tmp_path / "missing.pdf"
        # Don't create the file

        stale_hash = "stale-missing"
        rule_id = "test-rule-id"

        mock_db.get_doc_registry_url_hashes_by_repo.return_value = [stale_hash]
        mock_db.get_rule_id_by_url_hash.return_value = rule_id
        mock_db.get_rule_reference_paths.return_value = [ref_path]  # Path exists but file doesn't

        worker = GenericDiscoveryWorker(
            db=mock_db, source_type=SourceType.GITHUB, base_dir=tmp_path
        )

        repo_items = [("org", "repo")]
        # Pass a dummy active entry so GC doesn't return early
        active_entry = {"url_hash": "active-dummy", "org": "org", "repo": "repo"}
        current_entries: list[dict] = [active_entry]

        worker._garbage_collect_github(repo_items, current_entries)

        # Verify: no error, deletion is idempotent (missing_ok=True)
        mock_db.delete_doc_registry_by_url_hashes.assert_called_once_with([stale_hash])
