"""Tests for EmbeddingWorker base class error paths and binary parsing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from llama_index.core.schema import Document

from src.back.utils.identify_file_type import FileType
from src.worker.workers.generic_embedding_worker import GenericEmbeddingWorker


def _make_worker(cls, mock_db: MagicMock) -> tuple:
    worker = cls(mock_db, MagicMock())
    return worker, MagicMock()


def _make_sigmaref_entry(
    url_hash: str = "hash001",
    file_name: str = "hash001.md",
    content_type: str = "markdown",
    **overrides,
) -> dict:
    return {
        "url_hash": url_hash,
        "file_name": file_name,
        "org": "sigmaref",
        "original_url": "https://example.com/doc",
        "content_type": content_type,
        "rule_id": "rule-001",
        "title": "Test Doc",
        "embed_status": "discovered",
        **overrides,
    }


class TestEmbeddingBaseParseBinary:
    """Tests for _parse_binary_document dispatch."""

    def _worker(self) -> GenericEmbeddingWorker:
        return GenericEmbeddingWorker(MagicMock(), MagicMock())

    @patch("llama_index.readers.file.PyMuPDFReader")
    def test_parses_pdf(self, MockReader: MagicMock) -> None:
        fake_docs = [Document(text="pdf content")]
        MockReader.return_value.load_data.return_value = fake_docs

        worker = self._worker()
        result = worker._parse_binary_document(Path("doc.pdf"), FileType.PDF.value)

        assert result == fake_docs
        MockReader.return_value.load_data.assert_called_once_with(Path("doc.pdf"))

    @patch("llama_index.readers.file.DocxReader")
    def test_parses_docx(self, MockReader: MagicMock) -> None:
        fake_docs = [Document(text="docx content")]
        MockReader.return_value.load_data.return_value = fake_docs

        worker = self._worker()
        result = worker._parse_binary_document(Path("doc.docx"), FileType.OFFICE_DOCUMENT.value)

        assert result == fake_docs
        MockReader.return_value.load_data.assert_called_once_with(Path("doc.docx"))

    @patch("llama_index.readers.file.DocxReader")
    def test_parses_doc(self, MockReader: MagicMock) -> None:
        fake_docs = [Document(text="doc content")]
        MockReader.return_value.load_data.return_value = fake_docs

        worker = self._worker()
        result = worker._parse_binary_document(Path("old.doc"), FileType.OFFICE_DOCUMENT.value)

        assert result == fake_docs

    @patch("llama_index.readers.file.PptxReader")
    def test_parses_pptx(self, MockReader: MagicMock) -> None:
        fake_docs = [Document(text="slide content")]
        MockReader.return_value.load_data.return_value = fake_docs

        worker = self._worker()
        result = worker._parse_binary_document(Path("deck.pptx"), FileType.OFFICE_DOCUMENT.value)

        assert result == fake_docs

    @patch("llama_index.readers.file.PptxReader")
    def test_parses_ppt(self, MockReader: MagicMock) -> None:
        fake_docs = [Document(text="old slide")]
        MockReader.return_value.load_data.return_value = fake_docs

        worker = self._worker()
        result = worker._parse_binary_document(Path("deck.ppt"), FileType.OFFICE_DOCUMENT.value)

        assert result == fake_docs

    def test_raises_on_unsupported_office_format(self) -> None:
        worker = self._worker()
        with pytest.raises(ValueError, match="Unsupported office format"):
            worker._parse_binary_document(Path("data.xlsx"), FileType.OFFICE_DOCUMENT.value)

    def test_raises_on_unsupported_content_type(self) -> None:
        worker = self._worker()
        with pytest.raises(ValueError, match="Unsupported binary format"):
            worker._parse_binary_document(Path("file.xyz"), "unknown_format")


class TestEmbeddingBaseBinaryProcess:
    """Integration tests: process() flow for binary documents."""

    def _make_task(self, registry_dir: str) -> dict:
        return {
            "task_id": "bin-emb-001",
            "collection_name": "sigmaref",
            "registry_path": registry_dir,
        }

    def test_embeds_pdf_via_sigmaref_worker(self, mock_db: MagicMock, tmp_path: Path) -> None:
        registry_dir = tmp_path / "sigmaref"
        registry_dir.mkdir(exist_ok=True)
        pdf_file = registry_dir / "hash001.pdf"
        pdf_file.write_text("dummy pdf content")

        mock_db.get_pending_entries.return_value = [
            _make_sigmaref_entry(
                url_hash="hash001",
                file_name="hash001.pdf",
                content_type=FileType.PDF.value,
            )
        ]

        task = {
            "task_id": "bin-emb-001",
            "collection_name": "sigmaref",
            "org": "sigmaref",
            "registry_path": str(registry_dir),
        }

        fake_docs = [Document(text="extracted pdf text", metadata={"page": 1})]

        with (
            patch("src.worker.workers.embedding_base.IngestionPipelineBuilder") as mock_builder_cls,
            patch.object(
                GenericEmbeddingWorker,
                "_parse_binary_document",
                return_value=fake_docs,
            ) as mock_parse,
            patch.object(
                GenericEmbeddingWorker,
                "_resolve_file_path",
                return_value=pdf_file,
            ),
        ):
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, _ = _make_worker(GenericEmbeddingWorker, mock_db)
            worker.process(task)

        mock_parse.assert_called_once()
        mock_builder.run.assert_called_once()
        mock_db.update_doc_registry_embed_status.assert_called_with("hash001", "embedded")

    def test_embeds_docx_via_sigmaref_worker(self, mock_db: MagicMock, tmp_path: Path) -> None:
        registry_dir = tmp_path / "sigmaref"
        registry_dir.mkdir()
        docx_file = registry_dir / "hash002.docx"
        docx_file.write_text("dummy docx")

        mock_db.get_pending_entries.return_value = [
            _make_sigmaref_entry(
                url_hash="hash002",
                file_name="hash002.docx",
                content_type=FileType.OFFICE_DOCUMENT.value,
            )
        ]

        task = {
            "task_id": "bin-emb-002",
            "collection_name": "sigmaref",
            "org": "sigmaref",
            "registry_path": str(registry_dir),
        }

        with (
            patch("src.worker.workers.embedding_base.IngestionPipelineBuilder") as mock_builder_cls,
            patch.object(
                GenericEmbeddingWorker,
                "_parse_binary_document",
                return_value=[Document(text="extracted text")],
            ) as mock_parse,
            patch.object(
                GenericEmbeddingWorker,
                "_resolve_file_path",
                return_value=docx_file,
            ),
        ):
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, _ = _make_worker(GenericEmbeddingWorker, mock_db)
            worker.process(task)

        mock_parse.assert_called_once()
        mock_builder.run.assert_called_once()
        mock_db.update_doc_registry_embed_status.assert_called_with("hash002", "embedded")

    def test_skips_unsupported_office_format(self, mock_db: MagicMock, tmp_path: Path) -> None:
        registry_dir = tmp_path / "sigmaref"
        registry_dir.mkdir()
        xlsx_file = registry_dir / "data.xlsx"
        xlsx_file.write_text("fake excel")

        mock_db.get_pending_entries.return_value = [
            _make_sigmaref_entry(
                url_hash="xls001",
                file_name="data.xlsx",
                content_type=FileType.OFFICE_DOCUMENT.value,
            )
        ]

        task = {
            "task_id": "bin-emb-003",
            "collection_name": "sigmaref",
            "org": "sigmaref",
            "registry_path": str(registry_dir),
        }

        with (
            patch("src.worker.workers.embedding_base.IngestionPipelineBuilder") as mock_builder_cls,
            patch.object(
                GenericEmbeddingWorker,
                "_resolve_file_path",
                return_value=xlsx_file,
            ),
        ):
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, _ = _make_worker(GenericEmbeddingWorker, mock_db)
            worker.process(task)

        mock_builder.run.assert_not_called()
        mock_db.update_doc_registry_embed_status.assert_called_with("xls001", "skipped")

    def test_handles_binary_parse_error(self, mock_db: MagicMock, tmp_path: Path) -> None:
        registry_dir = tmp_path / "sigmaref"
        registry_dir.mkdir()
        bad_file = registry_dir / "bad.pdf"
        bad_file.write_text("not a real pdf")

        mock_db.get_pending_entries.return_value = [
            _make_sigmaref_entry(
                url_hash="bad001",
                file_name="bad.pdf",
                content_type=FileType.PDF.value,
            )
        ]

        task = {
            "task_id": "bin-emb-004",
            "collection_name": "sigmaref",
            "org": "sigmaref",
            "registry_path": str(registry_dir),
        }

        with (
            patch("src.worker.workers.embedding_base.IngestionPipelineBuilder") as mock_builder_cls,
            patch.object(
                GenericEmbeddingWorker,
                "_parse_binary_document",
                side_effect=RuntimeError("parser crashed"),
            ),
            patch.object(
                GenericEmbeddingWorker,
                "_resolve_file_path",
                return_value=bad_file,
            ),
        ):
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, _ = _make_worker(GenericEmbeddingWorker, mock_db)
            worker.process(task)

        mock_builder.run.assert_not_called()
        mock_db.update_doc_registry_embed_status.assert_called_with("bad001", "error")

    def test_merges_metadata_from_reader(self, mock_db: MagicMock, tmp_path: Path) -> None:
        registry_dir = tmp_path / "sigmaref"
        registry_dir.mkdir()
        meta_file = registry_dir / "meta001.pdf"
        meta_file.write_text("dummy")

        mock_db.get_pending_entries.return_value = [
            _make_sigmaref_entry(
                url_hash="meta001",
                file_name="meta001.pdf",
                content_type=FileType.PDF.value,
                title="Important Doc",
            )
        ]

        task = {
            "task_id": "bin-emb-005",
            "collection_name": "sigmaref",
            "org": "sigmaref",
            "registry_path": str(registry_dir),
        }

        reader_doc = Document(
            text="page text",
            metadata={"page_label": "1", "file_path": "/some/path"},
        )
        fake_docs = [reader_doc]

        with (
            patch("src.worker.workers.embedding_base.IngestionPipelineBuilder") as mock_builder_cls,
            patch.object(
                GenericEmbeddingWorker,
                "_parse_binary_document",
                return_value=fake_docs,
            ),
            patch.object(
                GenericEmbeddingWorker,
                "_resolve_file_path",
                return_value=meta_file,
            ),
        ):
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, _ = _make_worker(GenericEmbeddingWorker, mock_db)
            worker.process(task)

        passed_docs = mock_builder.run.call_args[1]["documents"]
        assert len(passed_docs) == 1
        merged = passed_docs[0].metadata
        assert merged["title"] == "Important Doc"
        assert merged["page_label"] == "1"
        assert merged["source"] == "sigma_docs"

    def test_handles_mixed_binary_and_text_entries(
        self, mock_db: MagicMock, tmp_path: Path
    ) -> None:
        registry_dir = tmp_path / "sigmaref"
        registry_dir.mkdir()
        pdf_file = registry_dir / "hash001.pdf"
        pdf_file.write_text("dummy")
        md_file = registry_dir / "hash002.md"
        md_file.write_text("# Markdown doc")

        mock_db.get_pending_entries.return_value = [
            _make_sigmaref_entry(
                url_hash="hash001",
                file_name="hash001.pdf",
                content_type=FileType.PDF.value,
                title="PDF Doc",
            ),
            _make_sigmaref_entry(
                url_hash="hash002",
                file_name="hash002.md",
                content_type="markdown",
                title="MD Doc",
            ),
        ]

        task = {
            "task_id": "bin-emb-006",
            "collection_name": "sigmaref",
            "org": "sigmaref",
            "registry_path": str(registry_dir),
        }

        def resolve_side_effect(entry):
            if entry.get("file_name") == "hash001.pdf":
                return pdf_file
            return md_file

        with (
            patch("src.worker.workers.embedding_base.IngestionPipelineBuilder") as mock_builder_cls,
            patch.object(
                GenericEmbeddingWorker,
                "_parse_binary_document",
                return_value=[Document(text="extracted pdf")],
            ) as mock_parse,
            patch.object(
                GenericEmbeddingWorker,
                "_resolve_file_path",
                side_effect=resolve_side_effect,
            ),
        ):
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, _ = _make_worker(GenericEmbeddingWorker, mock_db)
            worker.process(task)

        mock_parse.assert_called_once()
        assert mock_builder.run.call_count == 2
        calls = mock_db.update_doc_registry_embed_status.call_args_list
        statuses = {c[0][0]: c[0][1] for c in calls}
        assert statuses["hash001"] == "embedded"
        assert statuses["hash002"] == "embedded"


class TestEmbeddingBaseReadError:
    def test_handles_read_failure(self, mock_db: MagicMock, tmp_path: Path) -> None:
        registry_dir = tmp_path / "sigmaref"
        registry_dir.mkdir()
        bad_file = registry_dir / "bad123.md"
        bad_file.write_text("ok", encoding="utf-8")

        mock_db.get_pending_entries.return_value = [
            {
                "url_hash": "bad123",
                "org": "sigmaref",
                "original_url": "https://example.com/doc",
                "content_type": "markdown",
                "embed_status": "discovery",
            }
        ]

        task = {
            "task_id": "err-001",
            "collection_name": "sigmaref",
            "org": "sigmaref",
            "registry_path": str(registry_dir),
        }

        with (
            patch("src.worker.workers.embedding_base.IngestionPipelineBuilder") as mock_builder_cls,
            patch("pathlib.Path.read_text", side_effect=PermissionError("denied")),
            patch.object(
                GenericEmbeddingWorker,
                "_resolve_file_path",
                return_value=bad_file,
            ),
        ):
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, _ = _make_worker(GenericEmbeddingWorker, mock_db)
            worker.process(task)

        mock_db.update_doc_registry_embed_status.assert_called_with("bad123", "error")

    def test_handles_builder_run_failure(self, mock_db: MagicMock, tmp_path: Path) -> None:
        registry_dir = tmp_path / "sigmaref"
        registry_dir.mkdir()
        abc_file = registry_dir / "abc123.md"
        abc_file.write_text("# Test")

        mock_db.get_pending_entries.return_value = [
            {
                "url_hash": "abc123",
                "org": "sigmaref",
                "original_url": "https://example.com/doc",
                "content_type": "markdown",
                "embed_status": "discovery",
            }
        ]

        task = {
            "task_id": "err-002",
            "collection_name": "sigmaref",
            "org": "sigmaref",
            "registry_path": str(registry_dir),
        }

        with (
            patch("src.worker.workers.embedding_base.IngestionPipelineBuilder") as mock_builder_cls,
            patch.object(
                GenericEmbeddingWorker,
                "_resolve_file_path",
                return_value=abc_file,
            ),
        ):
            mock_builder = MagicMock()
            mock_builder.run = MagicMock(side_effect=ValueError("embedding failed"))
            mock_builder_cls.return_value = mock_builder

            worker, _ = _make_worker(GenericEmbeddingWorker, mock_db)
            worker.process(task)

        mock_db.update_doc_registry_embed_status.assert_called_with("abc123", "error")


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
            "org": "local",
            "collection_name": "local",
            "base_path": str(local_dir),
        }

        with (
            patch("src.worker.workers.embedding_base.IngestionPipelineBuilder") as mock_builder_cls,
            patch("pathlib.Path.read_text", side_effect=PermissionError("denied")),
            patch.object(
                GenericEmbeddingWorker,
                "_resolve_file_path",
                return_value=bad_file,
            ),
        ):
            mock_builder = MagicMock()
            mock_builder.run = MagicMock()
            mock_builder_cls.return_value = mock_builder

            worker, _ = _make_worker(GenericEmbeddingWorker, mock_db)
            worker.process(task)

        mock_db.update_doc_registry_embed_status.assert_called_with("hash1", "error")

    def test_local_builder_run_failure(self, mock_db: MagicMock, tmp_path: Path) -> None:
        local_dir = tmp_path / "docs"
        local_dir.mkdir()
        doc_file = local_dir / "doc.md"
        doc_file.write_text("# Doc")

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
            "org": "local",
            "collection_name": "local",
            "base_path": str(local_dir),
        }

        with (
            patch("src.worker.workers.embedding_base.IngestionPipelineBuilder") as mock_builder_cls,
            patch.object(
                GenericEmbeddingWorker,
                "_resolve_file_path",
                return_value=doc_file,
            ),
        ):
            mock_builder = MagicMock()
            mock_builder.run = MagicMock(side_effect=ValueError("embed failed"))
            mock_builder_cls.return_value = mock_builder

            worker, _ = _make_worker(GenericEmbeddingWorker, mock_db)
            worker.process(task)

        mock_db.update_doc_registry_embed_status.assert_called_with("hash1", "error")
