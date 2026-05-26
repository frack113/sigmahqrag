"""Tests for EmbeddingWorker base class error paths."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch


from src.worker.workers.sigmaref_embedding_worker import SigmaRefEmbeddingWorker
from src.worker.workers.local_embedding_worker import LocalEmbeddingWorker


def _make_worker(cls, mock_db: MagicMock) -> tuple:
    mock_dispatcher = MagicMock()
    worker = cls(mock_db, mock_dispatcher)
    return worker, mock_dispatcher


class TestEmbeddingBaseReadError:
    def test_handles_read_failure(self, mock_db: MagicMock, tmp_path: Path) -> None:
        registry_dir = tmp_path / "sigmaref"
        registry_dir.mkdir()
        bad_file = registry_dir / "bad123.md"
        bad_file.write_text("ok", encoding="utf-8")

        mock_db.get_pending_sigma_ref.return_value = [
            {
                "url_hash": "bad123",
                "original_url": "https://example.com/doc",
                "content_type": "markdown",
                "embed_status": "discovered",
            }
        ]

        task = {
            "task_id": "err-001",
            "collection_name": "sigmaref",
            "registry_path": str(registry_dir),
        }

        with (
            patch("src.worker.workers.embedding_base.IngestionPipelineBuilder") as mock_builder_cls,
            patch("pathlib.Path.read_text", side_effect=PermissionError("denied")),
        ):
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, _ = _make_worker(SigmaRefEmbeddingWorker, mock_db)
            worker.process(task)

        mock_db.update_sigma_ref_embed_status.assert_called_with("bad123", "error")

    def test_handles_builder_run_failure(self, mock_db: MagicMock, tmp_path: Path) -> None:
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
            "task_id": "err-002",
            "collection_name": "sigmaref",
            "registry_path": str(registry_dir),
        }

        with patch(
            "src.worker.workers.embedding_base.IngestionPipelineBuilder"
        ) as mock_builder_cls:
            mock_builder = MagicMock()
            mock_builder.run = MagicMock(side_effect=ValueError("embedding failed"))
            mock_builder_cls.return_value = mock_builder

            worker, _ = _make_worker(SigmaRefEmbeddingWorker, mock_db)
            worker.process(task)

        mock_db.update_sigma_ref_embed_status.assert_called_with("abc123", "error")


class TestEmbeddingBaseLocalReadError:
    def test_local_read_failure(self, mock_db: MagicMock, tmp_path: Path) -> None:
        local_dir = tmp_path / "docs"
        local_dir.mkdir()
        bad_file = local_dir / "bad.md"
        bad_file.write_text("ok")

        mock_db.get_pending_doc_registry.return_value = [
            {
                "url_hash": "hash1",
                "org": "local",
                "repo": "local",
                "file_name": "bad.md",
                "content_type": "markdown",
                "embed_status": "discovery",
            }
        ]

        task = {
            "task_id": "err-local-001",
            "collection_name": "local",
            "base_path": str(local_dir),
        }

        with (
            patch("src.worker.workers.embedding_base.IngestionPipelineBuilder") as mock_builder_cls,
            patch("pathlib.Path.read_text", side_effect=PermissionError("denied")),
        ):
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, _ = _make_worker(LocalEmbeddingWorker, mock_db)
            worker.process(task)

        mock_db.update_doc_registry_embed_status.assert_called_with("hash1", "error")

    def test_local_builder_run_failure(self, mock_db: MagicMock, tmp_path: Path) -> None:
        local_dir = tmp_path / "docs"
        local_dir.mkdir()
        (local_dir / "doc.md").write_text("# Doc")

        mock_db.get_pending_doc_registry.return_value = [
            {
                "url_hash": "hash1",
                "org": "local",
                "repo": "local",
                "file_name": "doc.md",
                "content_type": "markdown",
                "embed_status": "discovery",
            }
        ]

        task = {
            "task_id": "err-local-002",
            "collection_name": "local",
            "base_path": str(local_dir),
        }

        with patch(
            "src.worker.workers.embedding_base.IngestionPipelineBuilder"
        ) as mock_builder_cls:
            mock_builder = MagicMock()
            mock_builder.run = MagicMock(side_effect=ValueError("embed failed"))
            mock_builder_cls.return_value = mock_builder

            worker, _ = _make_worker(LocalEmbeddingWorker, mock_db)
            worker.process(task)

        mock_db.update_doc_registry_embed_status.assert_called_with("hash1", "error")
