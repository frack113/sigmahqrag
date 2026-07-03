"""Tests for sigma_ref_paths module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from src.application.documents.sigma_ref_paths import (
    resolve_rule_path,
    sigmaref_resolve_path,
    sigmaref_write_path,
    subdir_for,
)


class TestSubdirFor:
    def test_markdown(self) -> None:
        assert subdir_for("markdown") == "markdown"

    def test_pdf(self) -> None:
        assert subdir_for("pdf") == "pdf"

    def test_html(self) -> None:
        assert subdir_for("html") == "html"

    def test_none(self) -> None:
        assert subdir_for(None) == "misc"

    def test_empty_string(self) -> None:
        assert subdir_for("") == "misc"

    def test_plain_text(self) -> None:
        assert subdir_for("plain_text") == "plain_text"

    def test_office_document(self) -> None:
        assert subdir_for("office_document") == "office"


class TestSigmarefWritePath:
    def test_basic_path(self, tmp_path: Path) -> None:
        result = sigmaref_write_path(tmp_path, "markdown", "doc.md")
        assert result == tmp_path / "markdown" / "doc.md"

    def test_pdf_path(self, tmp_path: Path) -> None:
        result = sigmaref_write_path(tmp_path, "pdf", "doc.pdf")
        assert result == tmp_path / "pdf" / "doc.pdf"

    def test_none_content_type(self, tmp_path: Path) -> None:
        result = sigmaref_write_path(tmp_path, None, "doc.txt")
        assert result == tmp_path / "misc" / "doc.txt"

    def test_html_path(self, tmp_path: Path) -> None:
        result = sigmaref_write_path(tmp_path, "html", "doc.html")
        assert result == tmp_path / "html" / "doc.html"


class TestSigmarefResolvePath:
    def test_existing_candidate_returns_candidate(self, tmp_path: Path) -> None:
        existing = tmp_path / "markdown" / "doc.md"
        existing.parent.mkdir(parents=True, exist_ok=True)
        existing.touch()

        result = sigmaref_resolve_path(tmp_path, "markdown", "doc.md")
        assert result == existing

    def test_non_existing_returns_default(self, tmp_path: Path) -> None:
        result = sigmaref_resolve_path(tmp_path, "markdown", "doc.md")
        assert result == tmp_path / "doc.md"

    def test_non_existing_pdf(self, tmp_path: Path) -> None:
        result = sigmaref_resolve_path(tmp_path, "pdf", "doc.pdf")
        assert result == tmp_path / "doc.pdf"


class TestResolveRulePath:
    def test_local_org(self) -> None:
        mock_cfg = MagicMock()
        mock_cfg.local_documents_path = "/tmp/local"
        result = resolve_rule_path({"org": "local", "file_name": "rule.yml"}, mock_cfg)
        assert result == Path("/tmp/local/rule.yml").resolve()

    def test_sigmaref_org_existing(self, tmp_path: Path) -> None:
        candidate = tmp_path / "markdown" / "rule.yml"
        candidate.parent.mkdir(parents=True, exist_ok=True)
        candidate.touch()

        mock_cfg = MagicMock()
        mock_cfg.sigmaref_documents_path = str(tmp_path)
        entry = {"org": "sigmaref", "file_name": "rule.yml", "content_type": "markdown"}
        result = resolve_rule_path(entry, mock_cfg)
        assert result == candidate

    def test_sigmaref_org_not_existing(self, tmp_path: Path) -> None:
        mock_cfg = MagicMock()
        mock_cfg.sigmaref_documents_path = str(tmp_path)
        entry = {"org": "sigmaref", "file_name": "rule.yml", "content_type": "markdown"}
        result = resolve_rule_path(entry, mock_cfg)
        assert result == tmp_path / "rule.yml"

    def test_github_org_repo(self) -> None:
        mock_cfg = MagicMock()
        mock_cfg.sigmaref_documents_path = "/tmp/sigmaref"
        entry = {"org": "sigma-project", "repo": "rules", "file_name": "rule.yml"}
        result = resolve_rule_path(entry, mock_cfg)
        assert result == Path("/tmp/sigmaref/sigma-project/rules/rule.yml")

    def test_empty_org_returns_none(self) -> None:
        mock_cfg = MagicMock()
        result = resolve_rule_path({"org": "", "file_name": "rule.yml"}, mock_cfg)
        assert result is None
