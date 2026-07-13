"""Tests for registry entry builder."""

from __future__ import annotations

from src.shared.utils.registry_utils import build_registry_entry


class TestBuildRegistryEntry:
    def test_minimal_entry(self) -> None:
        entry = build_registry_entry(
            normalized_url="https://example.com/doc.md",
            content_type="markdown",
            rule_id="rule-001",
            title="Test Rule",
        )
        assert entry["normalized_url"] == "https://example.com/doc.md"
        assert entry["content_type"] == "markdown"
        assert entry["rule_id"] == "rule-001"
        assert entry["title"] == "Test Rule"
        assert entry["org"] == "sigmaref"
        assert entry["repo"] == "references"
        assert entry["embed_status"] == "discovery"
        assert entry["file_name"] == "doc.md"
        assert entry["file_size"] == 0
        assert entry["url_hash"] != ""

    def test_with_url_hash(self) -> None:
        entry = build_registry_entry(
            normalized_url="https://example.com/doc.md",
            content_type="html",
            rule_id="rule-002",
            title="Another Rule",
            url_hash="abc123",
        )
        assert entry["url_hash"] == "abc123"

    def test_head_verified_status(self) -> None:
        entry = build_registry_entry(
            normalized_url="https://example.com/doc.md",
            content_type="html",
            rule_id="rule-003",
            title="Head Verified",
            embed_status="head_verified",
            file_size=1234,
        )
        assert entry["embed_status"] == "head_verified"
        assert entry["file_size"] == 1234

    def test_downloaded_entry(self) -> None:
        entry = build_registry_entry(
            normalized_url="https://example.com/doc.md",
            content_type="pdf",
            rule_id="rule-004",
            title="Downloaded Doc",
            content_sha256="abcdef1234567890",
            file_name="abc123.pdf",
            file_size=5678,
        )
        assert entry["content_sha256"] == "abcdef1234567890"
        assert entry["file_name"] == "abc123.pdf"
        assert entry["file_size"] == 5678
        assert entry["embed_status"] == "discovery"

    def test_original_url_falls_back(self) -> None:
        entry = build_registry_entry(
            normalized_url="https://example.com/doc.md",
            content_type="markdown",
            rule_id="rule-005",
            title="Fallback",
        )
        assert entry["original_url"] == "https://example.com/doc.md"

    def test_custom_original_url(self) -> None:
        entry = build_registry_entry(
            normalized_url="https://raw.githubusercontent.com/user/repo/doc.md",
            content_type="markdown",
            rule_id="rule-006",
            title="Custom Original",
            original_url="https://github.com/user/repo/blob/main/doc.md",
        )
        assert entry["original_url"] == "https://github.com/user/repo/blob/main/doc.md"
        assert entry["normalized_url"] == "https://raw.githubusercontent.com/user/repo/doc.md"

    def test_timestamp_is_set(self) -> None:
        entry = build_registry_entry(
            normalized_url="https://example.com/doc.md",
            content_type="markdown",
            rule_id="rule-007",
            title="Timestamp test",
        )
        assert entry["timestamp"] is not None
        assert entry["last_seen"] is not None
        assert entry["timestamp"] == entry["last_seen"]

    def test_file_name_from_url_when_not_given(self) -> None:
        entry = build_registry_entry(
            normalized_url="https://example.com/path/to/document.pdf",
            content_type="pdf",
            rule_id="rule-008",
            title="File name from URL",
        )
        assert entry["file_name"] == "document.pdf"
