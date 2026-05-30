"""Advanced tests for LocalDiscoveryWorker — error path coverage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.worker.workers.local_discovery_worker import LocalDiscoveryWorker


class TestLocalDiscoveryWorkerAdvanced:
    def test_process_handles_read_error(self, mock_db: MagicMock, tmp_path: Path) -> None:
        local_dir = tmp_path / "docs"
        local_dir.mkdir()
        test_file = local_dir / "doc.md"
        test_file.write_text("# Doc")

        task = {
            "task_id": "local-adv-001",
            "collection_name": "local",
            "base_path": str(local_dir),
        }

        worker = LocalDiscoveryWorker(mock_db)
        with patch.object(worker, "_compute_sha256", return_value=("", 0)):
            worker.process(task)
        mock_db.batch_upsert_doc_registry.assert_called_once()
        entries = mock_db.batch_upsert_doc_registry.call_args[0][0]
        assert entries[0]["content_sha256"] == ""
        assert entries[0]["file_size"] == 0

    def test_process_handles_identify_error(self, mock_db: MagicMock, tmp_path: Path) -> None:
        local_dir = tmp_path / "docs"
        local_dir.mkdir()
        (local_dir / "doc.unknown").write_text("# Doc")

        task = {
            "task_id": "local-adv-002",
            "collection_name": "local",
            "base_path": str(local_dir),
        }

        worker = LocalDiscoveryWorker(mock_db)
        with patch(
            "src.worker.workers.local_discovery_worker.SUPPORTED_DOC_EXTENSION_MAP",
            {".unknown": "unknown"},
        ):
            with patch(
                "src.worker.workers.local_discovery_worker.SUPPORTED_EXTENSIONS",
                frozenset({".unknown"}),
            ):
                with patch(
                    "src.worker.workers.discovery_base.identify",
                    side_effect=ValueError("unknown"),
                ):
                    worker.process(task)
                    # identify error handled gracefully by _identify_content_type
                    mock_db.batch_upsert_doc_registry.assert_called_once()
                    entries = mock_db.batch_upsert_doc_registry.call_args[0][0]
                    assert entries[0]["content_type"] == "unknown"
