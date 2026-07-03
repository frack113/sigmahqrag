"""Tests for sigma_ref_url module."""

from __future__ import annotations

from src.application.documents.sigma_ref_url import (
    detect_url_type,
    is_reference_url,
    resolve_ext,
)


class TestDetectUrlType:
    def test_markdown_extension(self) -> None:
        assert detect_url_type("https://example.com/doc.md") == "markdown"

    def test_markdown_extension_alt(self) -> None:
        assert detect_url_type("https://example.com/doc.markdown") == "markdown"

    def test_pdf_extension(self) -> None:
        assert detect_url_type("https://example.com/doc.pdf") == "pdf"

    def test_html_extension(self) -> None:
        assert detect_url_type("https://example.com/doc.html") == "html"

    def test_unsupported_extension(self) -> None:
        assert detect_url_type("https://example.com/doc.exe") is None

    def test_no_extension_with_markdown_content_type(self) -> None:
        assert (
            detect_url_type("https://example.com/doc", content_type="text/markdown") == "markdown"
        )

    def test_no_extension_with_pdf_content_type(self) -> None:
        assert detect_url_type("https://example.com/doc", content_type="application/pdf") == "pdf"

    def test_no_extension_with_html_content_type(self) -> None:
        assert detect_url_type("https://example.com/doc", content_type="text/html") == "html"

    def test_no_extension_with_text_content_type(self) -> None:
        assert detect_url_type("https://example.com/doc", content_type="text/plain") == "markdown"

    def test_no_extension_no_content_type(self) -> None:
        assert detect_url_type("https://example.com/doc") is None

    def test_content_type_takes_precedence(self) -> None:
        assert (
            detect_url_type("https://example.com/doc.md", content_type="application/pdf") == "pdf"
        )

    def test_empty_url(self) -> None:
        assert detect_url_type("") is None

    def test_plain_text_file_type(self) -> None:
        assert detect_url_type("https://example.com/doc.txt") == "plain_text"

    def test_office_document(self) -> None:
        assert detect_url_type("https://example.com/doc.docx") == "office_document"


class TestResolveExt:
    def test_with_content_type(self) -> None:
        assert resolve_ext("https://example.com/doc", "markdown") == ".md"

    def test_with_pdf_content_type(self) -> None:
        assert resolve_ext("https://example.com/doc", "pdf") == ".pdf"

    def test_fallback_to_url_extension(self) -> None:
        assert resolve_ext("https://example.com/doc.md", None) == ".md"

    def test_fallback_to_md(self) -> None:
        assert resolve_ext("https://example.com/doc", None) == ".md"

    def test_content_type_overrides_url(self) -> None:
        assert resolve_ext("https://example.com/doc.md", "pdf") == ".pdf"


class TestIsReferenceUrl:
    def test_github_raw(self) -> None:
        assert is_reference_url("https://github.com/user/repo/raw/main/doc.md") is True

    def test_github_blob(self) -> None:
        assert is_reference_url("https://github.com/user/repo/blob/main/doc.md") is True

    def test_gitlab_raw(self) -> None:
        assert is_reference_url("https://gitlab.com/user/repo/raw/main/doc.md") is True

    def test_bitbucket_raw(self) -> None:
        assert is_reference_url("https://bitbucket.org/user/repo/raw/main/doc.md") is True

    def test_rawcdn(self) -> None:
        assert is_reference_url("https://rawcdn.com/user/doc.md") is True

    def test_pastebin(self) -> None:
        assert is_reference_url("https://pastebin.com/abc123") is True

    def test_hastebin(self) -> None:
        assert is_reference_url("https://hastebin.com/abc123") is True

    def test_dpaste(self) -> None:
        assert is_reference_url("https://dpaste.org/abc123") is True

    def test_normal_url(self) -> None:
        assert is_reference_url("https://example.com/doc.md") is False

    def test_empty_url(self) -> None:
        assert is_reference_url("") is False

    def test_local_file(self) -> None:
        assert is_reference_url("file:///tmp/doc.md") is False
