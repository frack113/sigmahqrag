"""Tests for embedding workers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.back.worker.workers.github_embedding_worker import GithubEmbeddingWorker
from src.back.worker.workers.local_embedding_worker import LocalEmbeddingWorker
from src.back.worker.workers.sigmaref_embedding_worker import SigmaRefEmbeddingWorker


class TestSigmaRefEmbeddingWorker:
    @pytest.mark.asyncio
    async def test_process_completes_if_no_entries(self, mock_db: MagicMock) -> None:
        mock_db.get_doc_sigma_ref.return_value = []

        task = {
            "task_id": "sr-emb-001",
            "task_type": "sigmaref_embeddings",
            "collection_name": "sigmaref",
            "registry_path": "data/documents/sigmaref",
        }

        worker = SigmaRefEmbeddingWorker(mock_db)
        await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"
        assert final_call.kwargs["total"] == 0

    @pytest.mark.asyncio
    async def test_process_embeds_entries(self, mock_db: MagicMock, tmp_path: Path) -> None:
        registry_dir = tmp_path / "sigmaref"
        registry_dir.mkdir()
        (registry_dir / "abc123.md").write_text("# Test Doc")

        mock_db.get_doc_sigma_ref.return_value = [
            {
                "url_hash": "abc123",
                "original_url": "https://example.com/doc1",
                "content_type": "markdown",
                "rule_id": "rule-001",
                "title": "Test Doc",
            }
        ]

        task = {
            "task_id": "sr-emb-002",
            "task_type": "sigmaref_embeddings",
            "collection_name": "sigmaref",
            "registry_path": str(registry_dir),
        }

        with patch("src.back.worker.workers.sigmaref_embedding_worker.IngestionPipelineBuilder") as mock_builder_cls:
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker = SigmaRefEmbeddingWorker(mock_db)
            await worker.process(task)

        mock_builder.run.assert_called_once()
        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"
        assert final_call.kwargs["processed"] == 1

    @pytest.mark.asyncio
    async def test_process_skips_missing_files(self, mock_db: MagicMock, tmp_path: Path) -> None:
        registry_dir = tmp_path / "sigmaref"
        registry_dir.mkdir()

        mock_db.get_doc_sigma_ref.return_value = [
            {
                "url_hash": "missing123",
                "original_url": "https://example.com/missing",
                "content_type": "markdown",
                "rule_id": "rule-002",
                "title": "Missing Doc",
            }
        ]

        task = {
            "task_id": "sr-emb-003",
            "task_type": "sigmaref_embeddings",
            "collection_name": "sigmaref",
            "registry_path": str(registry_dir),
        }

        with patch("src.back.worker.workers.sigmaref_embedding_worker.IngestionPipelineBuilder") as mock_builder_cls:
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker = SigmaRefEmbeddingWorker(mock_db)
            await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"
        assert final_call.kwargs["skipped"] == 1

    @pytest.mark.asyncio
    async def test_process_reports_running_status(self, mock_db: MagicMock, tmp_path: Path) -> None:
        registry_dir = tmp_path / "sigmaref"
        registry_dir.mkdir()
        (registry_dir / "abc123.md").write_text("# Test")

        mock_db.get_doc_sigma_ref.return_value = [
            {"url_hash": "abc123", "original_url": "https://example.com/doc", "content_type": "markdown"}
        ]

        task = {
            "task_id": "sr-emb-004",
            "task_type": "sigmaref_embeddings",
            "collection_name": "sigmaref",
            "registry_path": str(registry_dir),
        }

        with patch("src.back.worker.workers.sigmaref_embedding_worker.IngestionPipelineBuilder") as mock_builder_cls:
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker = SigmaRefEmbeddingWorker(mock_db)
            await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        assert any(c.kwargs["status"] == "running" for c in calls)
        assert any(c.kwargs["status"] == "completed" for c in calls)

    @pytest.mark.asyncio
    async def test_process_reports_source_type(self, mock_db: MagicMock, tmp_path: Path) -> None:
        registry_dir = tmp_path / "sigmaref"
        registry_dir.mkdir()
        (registry_dir / "abc123.md").write_text("# Test")

        mock_db.get_doc_sigma_ref.return_value = [
            {"url_hash": "abc123", "original_url": "https://example.com/doc", "content_type": "markdown"}
        ]

        task = {
            "task_id": "sr-emb-005",
            "task_type": "sigmaref_embeddings",
            "collection_name": "sigmaref",
            "registry_path": str(registry_dir),
        }

        with patch("src.back.worker.workers.sigmaref_embedding_worker.IngestionPipelineBuilder") as mock_builder_cls:
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker = SigmaRefEmbeddingWorker(mock_db)
            await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        assert all(c.kwargs["source_type"] == "sigmaref_embeddings" for c in calls)


class TestGithubEmbeddingWorker:
    @pytest.mark.asyncio
    async def test_process_raises_if_path_missing(self, mock_db: MagicMock, tmp_path: Path) -> None:
        task = {
            "task_id": "gh-emb-001",
            "task_type": "github_embeddings",
            "collection_name": "test-org/test-repo",
        }

        def mock_path(*args):
            if args == ("data/github",):
                return tmp_path
            return tmp_path / "/".join(args)

        with patch("src.back.worker.workers.github_embedding_worker.Path", side_effect=mock_path):
            worker = GithubEmbeddingWorker(mock_db)
            with pytest.raises(FileNotFoundError, match="Repository path does not exist"):
                await worker.process(task)

    @pytest.mark.asyncio
    async def test_process_raises_invalid_collection_name(self, mock_db: MagicMock) -> None:
        task = {
            "task_id": "gh-emb-002",
            "task_type": "github_embeddings",
            "collection_name": "",
        }

        worker = GithubEmbeddingWorker(mock_db)
        with pytest.raises(ValueError, match="collection_name is required"):
            await worker.process(task)

    @pytest.mark.asyncio
    async def test_process_completes_if_no_registry_entries(self, mock_db: MagicMock, tmp_path: Path) -> None:
        repo_dir = tmp_path / "test-org" / "test-repo"
        repo_dir.mkdir(parents=True)

        mock_db.get_doc_registry.return_value = []

        task = {
            "task_id": "gh-emb-003",
            "task_type": "github_embeddings",
            "collection_name": "test-org/test-repo",
        }

        def mock_path(*args):
            if args == ("data/github",):
                return tmp_path
            return tmp_path / "/".join(args)

        with patch("src.back.worker.workers.github_embedding_worker.Path", side_effect=mock_path):
            with patch("src.back.worker.workers.github_embedding_worker.IngestionPipelineBuilder") as mock_builder_cls:
                mock_builder = MagicMock()
                mock_builder.run = MagicMock()
                mock_builder_cls.return_value = mock_builder

                worker = GithubEmbeddingWorker(mock_db)
                await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"
        assert final_call.kwargs["total"] == 0

    @pytest.mark.asyncio
    async def test_process_embeds_discovered_files(self, mock_db: MagicMock, tmp_path: Path) -> None:
        repo_dir = tmp_path / "test-org" / "test-repo" / "rules"
        repo_dir.mkdir(parents=True)
        (repo_dir / "rule1.md").write_text("# Rule 1")

        mock_db.get_doc_registry.return_value = [
            {
                "org": "test-org",
                "repo": "test-repo",
                "file_name": "rules/rule1.md",
                "content_type": "rules",
                "status": "discovered",
            }
        ]

        task = {
            "task_id": "gh-emb-004",
            "task_type": "github_embeddings",
            "collection_name": "test-org/test-repo",
        }

        def mock_path(*args):
            if args == ("data/github",):
                return tmp_path
            return tmp_path / "/".join(args)

        with patch("src.back.worker.workers.github_embedding_worker.Path", side_effect=mock_path):
            with patch("src.back.worker.workers.github_embedding_worker.IngestionPipelineBuilder") as mock_builder_cls:
                mock_builder = MagicMock()
                mock_builder.run = MagicMock()
                mock_builder_cls.return_value = mock_builder

                worker = GithubEmbeddingWorker(mock_db)
                await worker.process(task)

        mock_builder.run.assert_called_once()
        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"
        assert final_call.kwargs["processed"] == 1

    @pytest.mark.asyncio
    async def test_process_filters_by_org_and_repo(self, mock_db: MagicMock, tmp_path: Path) -> None:
        repo_dir = tmp_path / "test-org" / "test-repo"
        repo_dir.mkdir(parents=True)

        mock_db.get_doc_registry.return_value = [
            {"org": "other-org", "repo": "other-repo", "file_name": "doc.md", "status": "discovered"},
            {"org": "test-org", "repo": "test-repo", "file_name": "doc.md", "status": "discovered"},
        ]

        task = {
            "task_id": "gh-emb-005",
            "task_type": "github_embeddings",
            "collection_name": "test-org/test-repo",
        }

        def mock_path(*args):
            if args == ("data/github",):
                return tmp_path
            return tmp_path / "/".join(args)

        with patch("src.back.worker.workers.github_embedding_worker.Path", side_effect=mock_path):
            with patch("src.back.worker.workers.github_embedding_worker.IngestionPipelineBuilder") as mock_builder_cls:
                mock_builder = MagicMock()
                mock_builder.run = MagicMock()
                mock_builder_cls.return_value = mock_builder

                worker = GithubEmbeddingWorker(mock_db)
                await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["total"] == 1

    @pytest.mark.asyncio
    async def test_process_reports_source_type(self, mock_db: MagicMock, tmp_path: Path) -> None:
        repo_dir = tmp_path / "test-org" / "test-repo"
        repo_dir.mkdir(parents=True)

        mock_db.get_doc_registry.return_value = []

        task = {
            "task_id": "gh-emb-006",
            "task_type": "github_embeddings",
            "collection_name": "test-org/test-repo",
        }

        def mock_path(*args):
            if args == ("data/github",):
                return tmp_path
            return tmp_path / "/".join(args)

        with patch("src.back.worker.workers.github_embedding_worker.Path", side_effect=mock_path):
            with patch("src.back.worker.workers.github_embedding_worker.IngestionPipelineBuilder") as mock_builder_cls:
                mock_builder = MagicMock()
                mock_builder.run = MagicMock()
                mock_builder_cls.return_value = mock_builder

                worker = GithubEmbeddingWorker(mock_db)
                await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        assert all(c.kwargs["source_type"] == "github_embeddings" for c in calls)


class TestLocalEmbeddingWorker:
    @pytest.mark.asyncio
    async def test_process_completes_if_path_missing(self, mock_db: MagicMock) -> None:
        task = {
            "task_id": "local-emb-001",
            "task_type": "local_embeddings",
            "collection_name": "local",
            "base_path": "/nonexistent/path",
        }

        worker = LocalEmbeddingWorker(mock_db)
        await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"
        assert final_call.kwargs["total"] == 0

    @pytest.mark.asyncio
    async def test_process_completes_if_no_registry_entries(self, mock_db: MagicMock, tmp_path: Path) -> None:
        local_dir = tmp_path / "local_docs"
        local_dir.mkdir()

        mock_db.get_doc_registry.return_value = []

        task = {
            "task_id": "local-emb-002",
            "task_type": "local_embeddings",
            "collection_name": "local",
            "base_path": str(local_dir),
        }

        worker = LocalEmbeddingWorker(mock_db)
        await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"
        assert final_call.kwargs["total"] == 0

    @pytest.mark.asyncio
    async def test_process_embeds_discovered_files(self, mock_db: MagicMock, tmp_path: Path) -> None:
        local_dir = tmp_path / "local_docs"
        local_dir.mkdir()
        (local_dir / "doc1.md").write_text("# Local Doc 1")

        mock_db.get_doc_registry.return_value = [
            {
                "org": "local",
                "repo": "local",
                "file_name": "doc1.md",
                "content_type": "markdown",
                "status": "discovered",
            }
        ]

        task = {
            "task_id": "local-emb-003",
            "task_type": "local_embeddings",
            "collection_name": "local",
            "base_path": str(local_dir),
        }

        with patch("src.back.worker.workers.local_embedding_worker.IngestionPipelineBuilder") as mock_builder_cls:
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker = LocalEmbeddingWorker(mock_db)
            await worker.process(task)

        mock_builder.run.assert_called_once()
        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"
        assert final_call.kwargs["processed"] == 1

    @pytest.mark.asyncio
    async def test_process_filters_by_local_org(self, mock_db: MagicMock, tmp_path: Path) -> None:
        local_dir = tmp_path / "local_docs"
        local_dir.mkdir()

        mock_db.get_doc_registry.return_value = [
            {"org": "github", "repo": "some-repo", "file_name": "doc.md", "status": "discovered"},
            {"org": "local", "repo": "local", "file_name": "doc.md", "status": "discovered"},
        ]

        task = {
            "task_id": "local-emb-004",
            "task_type": "local_embeddings",
            "collection_name": "local",
            "base_path": str(local_dir),
        }

        with patch("src.back.worker.workers.local_embedding_worker.IngestionPipelineBuilder") as mock_builder_cls:
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker = LocalEmbeddingWorker(mock_db)
            await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["total"] == 1

    @pytest.mark.asyncio
    async def test_process_reports_source_type(self, mock_db: MagicMock, tmp_path: Path) -> None:
        local_dir = tmp_path / "local_docs"
        local_dir.mkdir()

        mock_db.get_doc_registry.return_value = []

        task = {
            "task_id": "local-emb-005",
            "task_type": "local_embeddings",
            "collection_name": "local",
            "base_path": str(local_dir),
        }

        worker = LocalEmbeddingWorker(mock_db)
        await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        assert all(c.kwargs["source_type"] == "local_embeddings" for c in calls)

    @pytest.mark.asyncio
    async def test_process_uses_default_path(self, mock_db: MagicMock) -> None:
        mock_db.get_doc_registry.return_value = []

        task = {
            "task_id": "local-emb-006",
            "task_type": "local_embeddings",
            "collection_name": "local",
        }

        worker = LocalEmbeddingWorker(mock_db)
        await worker.process(task)

        calls = mock_db.upsert_embed_progress.call_args_list
        final_call = calls[-1]
        assert final_call.kwargs["status"] == "completed"
