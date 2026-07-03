"""Tests for sigma_ref_registry module."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.application.documents.sigma_ref_registry import (
    load_error_registry,
    load_registry,
    maybe_record_error,
    save_registry,
)


class TestLoadRegistry:
    def test_loads_from_db(self) -> None:
        mock_db = MagicMock()
        mock_db.get_entries_by_org.return_value = [
            {
                "url_hash": "abc123",
                "original_url": "https://example.com/doc.md",
                "normalized_url": "https://example.com/doc.md",
                "content_type": "markdown",
                "rule_id": "test-rule",
                "title": "Test Rule",
                "timestamp": "2024-01-01T00:00:00Z",
                "content_sha256": "sha256hash",
                "embed_status": "discovery",
                "last_seen": "2024-01-01T00:00:00Z",
                "file_name": "doc.md",
            }
        ]

        result = load_registry("/tmp/output", mock_db)

        assert "abc123" in result
        assert result["abc123"]["content_type"] == "markdown"
        assert result["abc123"]["embed_status"] == "discovery"
        mock_db.get_entries_by_org.assert_called_once_with("sigmaref", limit=0)

    def test_empty_registry(self) -> None:
        mock_db = MagicMock()
        mock_db.get_entries_by_org.return_value = []

        result = load_registry("/tmp/output", mock_db)

        assert result == {}


class TestSaveRegistry:
    def test_saves_to_db(self) -> None:
        mock_db = MagicMock()
        registry = {
            "abc123": {
                "original_url": "https://example.com/doc.md",
                "normalized_url": "https://example.com/doc.md",
                "content_type": "markdown",
                "rule_id": "test-rule",
                "title": "Test Rule",
                "timestamp": "2024-01-01T00:00:00Z",
                "content_sha256": "sha256hash",
                "embed_status": "discovery",
                "last_seen": "2024-01-01T00:00:00Z",
                "file_name": "doc.md",
                "file_size": 1024,
                "org": "sigmaref",
                "repo": "references",
            }
        }

        save_registry(registry, "/tmp/output", mock_db)

        mock_db.batch_upsert_doc_registry.assert_called_once()
        rows = mock_db.batch_upsert_doc_registry.call_args[0][0]
        assert len(rows) == 1
        assert rows[0]["url_hash"] == "abc123"
        assert rows[0]["content_type"] == "markdown"
        assert rows[0]["embed_status"] == "discovery"
        assert rows[0]["file_size"] == 1024

    def test_empty_registry_noop(self) -> None:
        mock_db = MagicMock()
        save_registry({}, "/tmp/output", mock_db)
        mock_db.batch_upsert_doc_registry.assert_not_called()

    def test_non_dict_entry_skipped(self) -> None:
        mock_db = MagicMock()
        registry = {"abc123": "not a dict"}
        save_registry(registry, "/tmp/output", mock_db)
        mock_db.batch_upsert_doc_registry.assert_not_called()


class TestLoadErrorRegistry:
    def test_loads_errors(self) -> None:
        mock_db = MagicMock()
        mock_db.get_doc_errors.return_value = [
            {"url_hash": "abc123", "error_code": 404},
            {"url_hash": "def456", "error_code": 403},
        ]

        result = load_error_registry(mock_db)

        assert result == {"abc123", "def456"}

    def test_empty_errors(self) -> None:
        mock_db = MagicMock()
        mock_db.get_doc_errors.return_value = []

        result = load_error_registry(mock_db)

        assert result == set()

    def test_db_error_returns_empty_set(self) -> None:
        mock_db = MagicMock()
        mock_db.get_doc_errors.side_effect = Exception("DB error")

        result = load_error_registry(mock_db)

        assert result == set()


class TestMaybeRecordError:
    def test_records_404(self) -> None:
        mock_db = MagicMock()
        maybe_record_error(
            mock_db,
            url_hash="abc123",
            original_url="https://example.com/doc.md",
            normalized_url="https://example.com/doc.md",
            status_code=404,
            rule_id="test-rule",
            rule_title="Test Rule",
        )
        mock_db.upsert_doc_error.assert_called_once()
        args = mock_db.upsert_doc_error.call_args[0][0]
        assert args["error_code"] == 404
        assert args["error_message"] == "HTTP 404"

    def test_records_403(self) -> None:
        mock_db = MagicMock()
        maybe_record_error(
            mock_db,
            url_hash="abc123",
            original_url="https://example.com/doc.md",
            normalized_url="https://example.com/doc.md",
            status_code=403,
            rule_id="test-rule",
            rule_title="Test Rule",
        )
        mock_db.upsert_doc_error.assert_called_once()

    def test_records_301_redirect(self) -> None:
        mock_db = MagicMock()
        maybe_record_error(
            mock_db,
            url_hash="abc123",
            original_url="https://example.com/old",
            normalized_url="https://example.com/new",
            status_code=301,
            rule_id="test-rule",
            rule_title="Test Rule",
        )
        mock_db.upsert_doc_error.assert_called_once()

    def test_no_record_for_200(self) -> None:
        mock_db = MagicMock()
        maybe_record_error(
            mock_db,
            url_hash="abc123",
            original_url="https://example.com/doc.md",
            normalized_url="https://example.com/doc.md",
            status_code=200,
            rule_id="test-rule",
            rule_title="Test Rule",
        )
        mock_db.upsert_doc_error.assert_not_called()

    def test_no_record_for_500_retryable(self) -> None:
        mock_db = MagicMock()
        maybe_record_error(
            mock_db,
            url_hash="abc123",
            original_url="https://example.com/doc.md",
            normalized_url="https://example.com/doc.md",
            status_code=500,
            rule_id="test-rule",
            rule_title="Test Rule",
        )
        mock_db.upsert_doc_error.assert_not_called()

    def test_no_record_for_none_status(self) -> None:
        mock_db = MagicMock()
        maybe_record_error(
            mock_db,
            url_hash="abc123",
            original_url="https://example.com/doc.md",
            normalized_url="https://example.com/doc.md",
            status_code=None,
            rule_id="test-rule",
            rule_title="Test Rule",
        )
        mock_db.upsert_doc_error.assert_not_called()

    def test_no_record_for_502_retryable(self) -> None:
        mock_db = MagicMock()
        maybe_record_error(
            mock_db,
            url_hash="abc123",
            original_url="https://example.com/doc.md",
            normalized_url="https://example.com/doc.md",
            status_code=502,
            rule_id="test-rule",
            rule_title="Test Rule",
        )
        mock_db.upsert_doc_error.assert_not_called()

    def test_records_503_non_retryable(self) -> None:
        mock_db = MagicMock()
        maybe_record_error(
            mock_db,
            url_hash="abc123",
            original_url="https://example.com/doc.md",
            normalized_url="https://example.com/doc.md",
            status_code=503,
            rule_id="test-rule",
            rule_title="Test Rule",
        )
        # 503 is in RETRY_STATUSES, so should NOT be recorded
        mock_db.upsert_doc_error.assert_not_called()

    def test_records_500_non_retryable(self) -> None:
        mock_db = MagicMock()
        # 500 is in RETRY_STATUSES, so should NOT be recorded
        maybe_record_error(
            mock_db,
            url_hash="abc123",
            original_url="https://example.com/doc.md",
            normalized_url="https://example.com/doc.md",
            status_code=500,
            rule_id="test-rule",
            rule_title="Test Rule",
        )
        mock_db.upsert_doc_error.assert_not_called()

    def test_records_501_not_in_retry_statuses(self) -> None:
        mock_db = MagicMock()
        maybe_record_error(
            mock_db,
            url_hash="abc123",
            original_url="https://example.com/doc.md",
            normalized_url="https://example.com/doc.md",
            status_code=501,
            rule_id="test-rule",
            rule_title="Test Rule",
        )
        mock_db.upsert_doc_error.assert_called_once()
