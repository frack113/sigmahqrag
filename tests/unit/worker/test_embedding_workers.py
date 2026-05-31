"""Tests for embedding workers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.worker.enums import WorkerStatus
from src.worker.workers.github_embedding_worker import GithubEmbeddingWorker
from src.worker.workers.local_embedding_worker import LocalEmbeddingWorker
from src.worker.workers.sigmaref_embedding_worker import SigmaRefEmbeddingWorker


def _make_worker(cls, mock_db: MagicMock) -> tuple:
    """Create a worker with a mock dispatcher. Returns (worker, mock_dispatcher)."""
    mock_dispatcher = MagicMock()
    worker = cls(mock_db, mock_dispatcher)
    return worker, mock_dispatcher


class TestSigmaRefEmbeddingWorker:
    def test_process_completes_if_no_entries(self, mock_db: MagicMock) -> None:
        mock_db.get_pending_sigma_ref.return_value = []

        task = {
            "task_id": "sr-emb-001",
            "task_type": "sigmaref_embeddings",
            "collection_name": "sigmaref",
            "registry_path": "data/documents/sigmaref",
        }

        worker, mock_dispatcher = _make_worker(SigmaRefEmbeddingWorker, mock_db)
        worker.process(task)

        mock_db.get_pending_sigma_ref.assert_called()
        mock_dispatcher.update_worker_state.assert_not_called()

    def test_process_embeds_entries(self, mock_db: MagicMock, tmp_path: Path) -> None:
        registry_dir = tmp_path / "sigmaref"
        registry_dir.mkdir()
        (registry_dir / "abc123.md").write_text("# Test Doc")

        mock_db.get_pending_sigma_ref.return_value = [
            {
                "url_hash": "abc123",
                "original_url": "https://example.com/doc1",
                "content_type": "markdown",
                "rule_id": "rule-001",
                "title": "Test Doc",
                "embed_status": "discovered",
            }
        ]

        task = {
            "task_id": "sr-emb-002",
            "task_type": "sigmaref_embeddings",
            "collection_name": "sigmaref",
            "registry_path": str(registry_dir),
        }

        with patch(
            "src.worker.workers.embedding_base.IngestionPipelineBuilder"
        ) as mock_builder_cls:
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, mock_dispatcher = _make_worker(SigmaRefEmbeddingWorker, mock_db)
            worker.process(task)

        mock_builder.run.assert_called_once()
        mock_db.update_sigma_ref_embed_status.assert_called_with("abc123", "embedded")
        mock_dispatcher.update_worker_state.assert_called()

    def test_process_skips_missing_files(self, mock_db: MagicMock, tmp_path: Path) -> None:
        registry_dir = tmp_path / "sigmaref"
        registry_dir.mkdir()

        mock_db.get_pending_sigma_ref.return_value = [
            {
                "url_hash": "missing123",
                "original_url": "https://example.com/missing",
                "content_type": "markdown",
                "rule_id": "rule-002",
                "title": "Missing Doc",
                "embed_status": "discovered",
            }
        ]

        task = {
            "task_id": "sr-emb-003",
            "task_type": "sigmaref_embeddings",
            "collection_name": "sigmaref",
            "registry_path": str(registry_dir),
        }

        with patch(
            "src.worker.workers.embedding_base.IngestionPipelineBuilder"
        ) as mock_builder_cls:
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, mock_dispatcher = _make_worker(SigmaRefEmbeddingWorker, mock_db)
            worker.process(task)

        mock_db.update_sigma_ref_embed_status.assert_called_with("missing123", "error")

    def test_process_reports_running_status(self, mock_db: MagicMock, tmp_path: Path) -> None:
        registry_dir = tmp_path / "sigmaref"
        registry_dir.mkdir()
        (registry_dir / "abc123.md").write_text("# Test")

        mock_db.get_pending_sigma_ref.return_value = [
            {
                "url_hash": "abc123",
                "original_url": "https://example.com/doc",
                "content_type": "markdown",
                "embed_status": "discovered",
            }
        ]

        task = {
            "task_id": "sr-emb-004",
            "task_type": "sigmaref_embeddings",
            "collection_name": "sigmaref",
            "registry_path": str(registry_dir),
        }

        with patch(
            "src.worker.workers.embedding_base.IngestionPipelineBuilder"
        ) as mock_builder_cls:
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, mock_dispatcher = _make_worker(SigmaRefEmbeddingWorker, mock_db)
            worker.process(task)

        state_calls = mock_dispatcher.update_worker_state.call_args_list
        assert any(c.kwargs.get("status") == WorkerStatus.RUNNING for c in state_calls)
        mock_dispatcher.update_worker_state.assert_called()


class TestGithubEmbeddingWorker:
    def test_process_raises_if_path_missing(self, mock_db: MagicMock, tmp_path: Path) -> None:
        task = {
            "task_id": "gh-emb-001",
            "task_type": "github_embeddings",
            "collection_name": "test-org/test-repo",
        }

        def mock_path(*args):
            if args == ("data/github",):
                return tmp_path
            return tmp_path / "/".join(args)

        with patch("src.worker.workers.github_embedding_worker.Path", side_effect=mock_path):
            worker, _ = _make_worker(GithubEmbeddingWorker, mock_db)
            with pytest.raises(FileNotFoundError, match="Repository path does not exist"):
                worker.process(task)

    def test_process_raises_invalid_collection_name(self, mock_db: MagicMock) -> None:
        task = {
            "task_id": "gh-emb-002",
            "task_type": "github_embeddings",
            "collection_name": "",
        }

        worker, _ = _make_worker(GithubEmbeddingWorker, mock_db)
        with pytest.raises(ValueError, match="collection_name is required"):
            worker.process(task)

    def test_process_completes_if_no_registry_entries(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        mock_db.get_pending_registry_all.return_value = []

        task = {
            "task_id": "gh-emb-003",
            "task_type": "github_embeddings",
            "collection_name": "all",
        }

        with patch(
            "src.worker.workers.embedding_base.IngestionPipelineBuilder"
        ) as mock_builder_cls:
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, _ = _make_worker(GithubEmbeddingWorker, mock_db)
            worker.process(task)

        mock_db.get_pending_registry_all.assert_called()

    def test_process_embeds_discovered_files(self, mock_db: MagicMock, tmp_path: Path) -> None:
        repo_dir = tmp_path / "test-org" / "test-repo" / "rules"
        repo_dir.mkdir(parents=True)
        (repo_dir / "rule1.md").write_text("# Rule 1")

        mock_db.get_pending_registry_all.return_value = [
            {
                "url_hash": "hash1",
                "org": "test-org",
                "repo": "test-repo",
                "file_name": "rules/rule1.md",
                "content_type": "rules",
                "status": "discovered",
                "embed_status": "discovered",
            }
        ]

        task = {
            "task_id": "gh-emb-004",
            "task_type": "github_embeddings",
            "collection_name": "all",
        }

        def mock_resolve(entry):
            file_name = entry.get("file_name", "")
            return tmp_path / "test-org" / "test-repo" / file_name

        with patch.object(GithubEmbeddingWorker, "_resolve_file_path", side_effect=mock_resolve):
            with patch(
                "src.worker.workers.embedding_base.IngestionPipelineBuilder"
            ) as mock_builder_cls:
                mock_builder = MagicMock()
                mock_builder.run = MagicMock()
                mock_builder_cls.return_value = mock_builder

                worker, mock_dispatcher = _make_worker(GithubEmbeddingWorker, mock_db)
                worker.process(task)

        mock_builder.run.assert_called_once()
        mock_db.update_doc_registry_embed_status.assert_called()

    def test_process_filters_by_org_and_repo(self, mock_db: MagicMock, tmp_path: Path) -> None:
        mock_db.get_pending_registry_all.return_value = [
            {
                "url_hash": "hash2",
                "org": "test-org",
                "repo": "test-repo",
                "file_name": "doc.md",
                "status": "discovered",
                "embed_status": "discovered",
            },
        ]

        task = {
            "task_id": "gh-emb-005",
            "task_type": "github_embeddings",
            "collection_name": "all",
        }

        with patch(
            "src.worker.workers.embedding_base.IngestionPipelineBuilder"
        ) as mock_builder_cls:
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, _ = _make_worker(GithubEmbeddingWorker, mock_db)
            worker.process(task)

        mock_db.get_pending_registry_all.assert_called()


class TestLocalEmbeddingWorker:
    def test_process_completes_if_path_missing(self, mock_db: MagicMock) -> None:
        task = {
            "task_id": "local-emb-001",
            "task_type": "local_embeddings",
            "collection_name": "local",
            "base_path": "/nonexistent/path",
        }

        worker, mock_dispatcher = _make_worker(LocalEmbeddingWorker, mock_db)
        worker.process(task)

        # Should call get_pending_doc_registry
        mock_db.get_pending_doc_registry.assert_called_with(org="local", repo="local")

    def test_process_completes_if_no_registry_entries(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        local_dir = tmp_path / "local_docs"
        local_dir.mkdir()

        mock_db.get_pending_doc_registry.return_value = []

        task = {
            "task_id": "local-emb-002",
            "task_type": "local_embeddings",
            "collection_name": "local",
            "base_path": str(local_dir),
        }

        worker, mock_dispatcher = _make_worker(LocalEmbeddingWorker, mock_db)
        worker.process(task)

        # No entries means no processing and no update_worker_state calls
        mock_db.get_pending_doc_registry.assert_called_with(org="local", repo="local")
        mock_dispatcher.update_worker_state.assert_not_called()

    def test_process_embeds_discovered_files(self, mock_db: MagicMock, tmp_path: Path) -> None:
        local_dir = tmp_path / "local_docs"
        local_dir.mkdir()
        (local_dir / "doc1.md").write_text("# Local Doc 1")

        mock_db.get_pending_doc_registry.return_value = [
            {
                "url_hash": "hash1",
                "org": "local",
                "repo": "local",
                "file_name": "doc1.md",
                "content_type": "markdown",
                "embed_status": "discovery",
            }
        ]

        task = {
            "task_id": "local-emb-003",
            "task_type": "local_embeddings",
            "collection_name": "local",
            "base_path": str(local_dir),
        }

        with patch(
            "src.worker.workers.embedding_base.IngestionPipelineBuilder"
        ) as mock_builder_cls:
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, mock_dispatcher = _make_worker(LocalEmbeddingWorker, mock_db)
            worker.process(task)

        mock_builder.run.assert_called_once()
        mock_db.update_doc_registry_embed_status.assert_any_call("hash1", "embedded")
        mock_dispatcher.update_worker_state.assert_called()

    def test_process_skips_missing_files(self, mock_db: MagicMock, tmp_path: Path) -> None:
        local_dir = tmp_path / "local_docs"
        local_dir.mkdir()

        mock_db.get_pending_doc_registry.return_value = [
            {
                "url_hash": "missing123",
                "org": "local",
                "repo": "local",
                "file_name": "missing.md",
                "content_type": "markdown",
                "embed_status": "discovery",
            }
        ]

        task = {
            "task_id": "local-emb-004",
            "task_type": "local_embeddings",
            "collection_name": "local",
            "base_path": str(local_dir),
        }

        with patch(
            "src.worker.workers.embedding_base.IngestionPipelineBuilder"
        ) as mock_builder_cls:
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, mock_dispatcher = _make_worker(LocalEmbeddingWorker, mock_db)
            worker.process(task)

        # Should mark as error when file is missing (no valid_docs so builder.run never called)
        mock_db.update_doc_registry_embed_status.assert_any_call("missing123", "error")

    def test_process_uses_default_path(self, mock_db: MagicMock) -> None:
        mock_db.get_pending_doc_registry.return_value = []

        task = {
            "task_id": "local-emb-006",
            "task_type": "local_embeddings",
            "collection_name": "local",
        }

        worker, mock_dispatcher = _make_worker(LocalEmbeddingWorker, mock_db)
        worker.process(task)

        # Uses default path but no entries, so nothing happens
        mock_db.get_pending_doc_registry.assert_called_with(org="local", repo="local")
        mock_dispatcher.update_worker_state.assert_not_called()
