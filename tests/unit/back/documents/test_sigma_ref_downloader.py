"""Tests for the Sigma reference downloader module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import ANY, MagicMock, patch

import httpx

from src.shared.utils import iso_now

from src.back.documents.sigma_ref_downloader import (
    _backoff_delay,
    _detect_url_type,
    _download_file,
    _get_retry_after,
    _is_private_url,
    _load_registry,
    _registry_lock,
    _save_registry,
    _sha256,
    _sha256_file,
    download_references,
    normalize_url,
)


def _make_db(entries: list[dict] | None = None) -> MagicMock:
    """Create a mock DatabaseService with in-memory doc_sigma_ref."""

    data: dict[str, dict] = {}
    if entries:
        for e in entries:
            data[e["url_hash"]] = dict(e)

    def get_doc_sigma_ref() -> list[dict]:
        return [
            {
                "url_hash": k,
                "original_url": v.get("original_url", ""),
                "normalized_url": v.get("normalized_url"),
                "content_type": v.get("content_type"),
                "rule_id": v.get("rule_id"),
                "title": v.get("title"),
                "timestamp": v.get("timestamp"),
                "content_sha256": v.get("content_sha256"),
            }
            for k, v in data.items()
        ]

    def upsert_doc_sigma_ref(entry: dict) -> None:
        data[entry["url_hash"]] = dict(entry)

    db = MagicMock()
    db.get_doc_sigma_ref = get_doc_sigma_ref
    db.upsert_doc_sigma_ref = upsert_doc_sigma_ref
    return db


class TestIsPrivateUrl:
    def test_localhost(self) -> None:
        assert _is_private_url("http://localhost/doc.md") is True

    def test_private_ip(self) -> None:
        assert _is_private_url("http://10.0.0.1/doc.md") is True

    def test_public_ip(self) -> None:
        assert _is_private_url("http://8.8.8.8/doc.md") is False

    def test_invalid_host(self) -> None:
        assert _is_private_url("http://not-an-ip/doc.md") is False


class TestNormalizeUrl:
    def test_github_blob_main(self) -> None:
        url = "https://github.com/user/repo/blob/main/doc.md"
        assert normalize_url(url) == "https://raw.githubusercontent.com/user/repo/main/doc.md"

    def test_github_blob_commit_sha(self) -> None:
        url = "https://github.com/user/repo/blob/abc123def456/doc.md"
        assert (
            normalize_url(url) == "https://raw.githubusercontent.com/user/repo/abc123def456/doc.md"
        )

    def test_github_blob_refs_heads(self) -> None:
        url = "https://github.com/user/repo/blob/refs/heads/feature/doc.md"
        assert normalize_url(url) == "https://raw.githubusercontent.com/user/repo/feature/doc.md"

    def test_github_blob_with_query(self) -> None:
        url = "https://github.com/user/repo/blob/main/doc.md?raw=true"
        assert normalize_url(url) == "https://raw.githubusercontent.com/user/repo/main/doc.md"

    def test_non_github_url_pass_through(self) -> None:
        url = "https://learn.microsoft.com/en-us/doc"
        assert normalize_url(url) == url

    def test_already_raw_github(self) -> None:
        url = "https://raw.githubusercontent.com/user/repo/main/doc.md"
        assert normalize_url(url) == url

    def test_strip_fragment(self) -> None:
        url = "https://example.com/page.html#section"
        assert normalize_url(url) == "https://example.com/page.html"

    def test_github_blob_with_fragment(self) -> None:
        url = "https://github.com/user/repo/blob/main/doc.md#section"
        assert normalize_url(url) == "https://raw.githubusercontent.com/user/repo/main/doc.md"


class TestDetectUrlType:
    def test_markdown_extension(self) -> None:
        assert _detect_url_type("https://example.com/doc.md") == "markdown"

    def test_markdown_extension_alt(self) -> None:
        assert _detect_url_type("https://example.com/doc.markdown") == "markdown"

    def test_unsupported_extension(self) -> None:
        assert _detect_url_type("https://example.com/doc.pdf") is None

    def test_no_extension_with_markdown_content_type(self) -> None:
        assert (
            _detect_url_type("https://example.com/doc", content_type="text/markdown") == "markdown"
        )

    def test_no_extension_no_content_type(self) -> None:
        assert _detect_url_type("https://example.com/doc") is None

    def test_empty_path(self) -> None:
        assert _detect_url_type("https://example.com") is None

    def test_text_plain_with_md_extension(self) -> None:
        assert (
            _detect_url_type("https://example.com/doc.md", content_type="text/plain") == "markdown"
        )


class TestDownloadFile:
    def test_successful_download(self, tmp_path: Path) -> None:
        url = "https://raw.githubusercontent.com/user/repo/main/test.md"
        output = tmp_path / "test.md"

        with patch("httpx.Client") as mock_client:
            mock_response = mock_client.return_value.__enter__.return_value.get.return_value
            mock_response.raise_for_status.return_value = None
            mock_response.content = b"# Hello"
            mock_response.status_code = 200

            result = _download_file(url, output, timeout=30)
            assert result is True
            assert output.read_text() == "# Hello"

    def test_retry_then_success(self, tmp_path: Path) -> None:
        url = "https://example.com/doc.md"
        output = tmp_path / "doc.md"
        attempts: list[int] = []

        class FakeResponse:
            status_code = 200
            headers = {}
            content = b"success"

            def raise_for_status(self) -> None:
                pass

        class FakeErrorResponse:
            status_code = 500
            headers = {}
            content = b""

        def mock_get(client_self, url: str, **kwargs: object) -> FakeResponse:
            attempts.append(len(attempts) + 1)
            if len(attempts) < 3:
                resp = FakeErrorResponse()
                raise httpx.HTTPStatusError("Server error", request=ANY, response=resp)  # type: ignore[arg-type]
            return FakeResponse()

        with patch.object(httpx.Client, "get", mock_get), patch("time.sleep"):
            result = _download_file(url, output, timeout=30)
            assert result is True
            assert output.read_text() == "success"
            assert len(attempts) == 3

    def test_all_retries_fail(self, tmp_path: Path) -> None:
        url = "https://example.com/fail.md"
        output = tmp_path / "fail.md"

        class ErrorResp:
            status_code = 500
            headers = {}

        def failing_get(self, url, **kwargs):
            raise httpx.HTTPStatusError("500", request=ANY, response=ErrorResp())

        with patch.object(httpx.Client, "get", failing_get):
            with patch("time.sleep"):
                result = _download_file(url, output, timeout=30)
                assert result is False
                assert not output.exists()

    def test_zero_retries(self, tmp_path: Path) -> None:
        url = "https://example.com/zero.md"
        output = tmp_path / "zero.md"

        call_count = 0

        def failing_get(self, url, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("connection failed")

        with patch.object(httpx.Client, "get", failing_get):
            result = _download_file(url, output, max_retries=0)
            assert result is False
            assert call_count == 0

    def test_network_error_retries(self, tmp_path: Path) -> None:
        url = "https://example.com/net.md"
        output = tmp_path / "net.md"

        call_count = 0

        def failing_get(self, url, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("connection refused")

        with patch.object(httpx.Client, "get", failing_get):
            with patch("time.sleep"):
                result = _download_file(url, output, timeout=30)
                assert result is False
                assert call_count == 3


class TestRegistry:
    def test_load_empty(self, tmp_path: Path) -> None:
        db = _make_db()
        reg = _load_registry(tmp_path, db)
        assert reg == {}

    def test_load_valid(self, tmp_path: Path) -> None:
        db = _make_db(
            entries=[
                {
                    "url_hash": "abc",
                    "original_url": "https://example.com/doc.md",
                    "normalized_url": "https://example.com/doc.md",
                }
            ]
        )
        reg = _load_registry(tmp_path, db)
        assert reg == {
            "abc": {
                "original_url": "https://example.com/doc.md",
                "normalized_url": "https://example.com/doc.md",
                "content_type": None,
                "rule_id": None,
                "title": None,
                "timestamp": None,
                "content_sha256": None,
            }
        }

    def test_save(self, tmp_path: Path) -> None:
        db = _make_db()
        data = {
            "abc": {
                "original_url": "https://example.com/doc.md",
                "timestamp": iso_now(),
            }
        }
        _save_registry(data, tmp_path, db)
        reg = _load_registry(tmp_path, db)
        assert "abc" in reg
        assert reg["abc"]["original_url"] == "https://example.com/doc.md"


class TestSha256:
    def test_consistent(self) -> None:
        assert (
            _sha256("hello") == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"
        )

    def test_different_inputs(self) -> None:
        assert _sha256("a") != _sha256("b")

    def test_empty_string(self) -> None:
        assert _sha256("") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"


class TestDownloadReferences:
    def test_skip_non_http_refs(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        rule = rules_dir / "test_rule.yml"
        rule.write_text("""
title: Test Rule
id: rule-001
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - mailto:test@example.com
  - ftp://files.example.com/doc.md
  - https://example.com/valid.md
""")

        db = _make_db()
        with patch(
            "src.back.documents.sigma_ref_downloader._download_file",
            return_value=True,
        ):
            result = download_references(str(rules_dir), str(tmp_path / "output"), db)
            assert result["downloaded"] == 1
            assert result["total_refs"] == 1

    def test_skip_unsupported_type(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        rule = rules_dir / "test_rule.yml"
        rule.write_text("""
title: Test Rule
id: rule-002
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://example.com/doc.pdf
""")

        db = _make_db()
        result = download_references(str(rules_dir), str(tmp_path / "output"), db)
        assert result["downloaded"] == 0
        assert result["skipped"] == 1
        assert result["total_rules"] == 1

    def test_duplicate_url_skipped(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        output_dir = tmp_path / "output"
        rule = rules_dir / "test_rule.yml"
        rule.write_text("""
title: Test Rule
id: rule-003
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://example.com/doc.md
""")

        db = _make_db()
        with patch(
            "src.back.documents.sigma_ref_downloader._download_file",
            return_value=True,
        ):
            first = download_references(str(rules_dir), str(output_dir), db)
            assert first["downloaded"] == 1

            second = download_references(str(rules_dir), str(output_dir), db)
            assert second["downloaded"] == 0
            assert second["skipped"] >= 1

    def test_github_blob_url_downloaded(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        output_dir = tmp_path / "output"
        rule = rules_dir / "test_rule.yml"
        rule.write_text("""
title: Test Rule
id: rule-004
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://github.com/user/repo/blob/main/docs/guide.md
""")

        def check_normalized_url(url: str, output_path: Path, timeout: int = 30) -> bool:
            assert "raw.githubusercontent.com" in url
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("# content")
            return True

        db = _make_db()
        with patch(
            "src.back.documents.sigma_ref_downloader._download_file",
            check_normalized_url,
        ):
            result = download_references(str(rules_dir), str(output_dir), db)
            assert result["downloaded"] == 1

            entries = db.get_doc_sigma_ref()
            entry = list(entries)[0]
            assert "raw.githubusercontent.com" in entry["normalized_url"]
            assert "/blob/" not in entry["normalized_url"]

    def test_empty_rules_dir(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        db = _make_db()
        result = download_references(str(empty_dir), str(tmp_path / "output"), db)
        assert result["total_rules"] == 0
        assert result["downloaded"] == 0

    def test_output_dir_created(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        output_dir = tmp_path / "nonexistent" / "sigmaref"
        rule = rules_dir / "test_rule.yml"
        rule.write_text("""
title: Test Rule
id: rule-005
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://example.com/test.md
""")

        db = _make_db()
        with patch(
            "src.back.documents.sigma_ref_downloader._download_file",
            return_value=True,
        ):
            result = download_references(str(rules_dir), str(output_dir), db)
            assert result["downloaded"] == 1
            assert output_dir.exists()

    def test_partial_download_cleanup(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        output_dir = tmp_path / "output"
        rule = rules_dir / "test_rule.yml"
        rule.write_text("""
title: Test Rule
id: rule-006
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://example.com/fail.md
""")

        db = _make_db()
        with patch(
            "src.back.documents.sigma_ref_downloader._download_file",
            return_value=False,
        ):
            result = download_references(str(rules_dir), str(output_dir), db)
            assert result["failed"] == 1
            assert result["downloaded"] == 0
            assert len(db.get_doc_sigma_ref()) == 0

    def test_same_filename_diff_content(self, tmp_path: Path) -> None:
        """Two different URLs with same filename -> stored under different hashes."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        output_dir = tmp_path / "output"
        rule = rules_dir / "test_rule.yml"
        rule.write_text("""
title: Test Rule
id: rule-007
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://example.com/a/readme.md
  - https://example.com/b/readme.md
""")

        urls_downloaded: list[str] = []

        def capture_url(url: str, output_path: Path, timeout: int = 30) -> bool:
            urls_downloaded.append(url)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("# content")
            return True

        db = _make_db()
        with patch("src.back.documents.sigma_ref_downloader._download_file", capture_url):
            result = download_references(str(rules_dir), str(output_dir), db)
            assert result["downloaded"] == 2
            assert len(urls_downloaded) == 2
            assert urls_downloaded[0] != urls_downloaded[1]

            assert len(db.get_doc_sigma_ref()) == 2


class TestContentSha256:
    def test_registry_entry_includes_content_sha256(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        output_dir = tmp_path / "output"
        rule = rules_dir / "test_rule.yml"
        rule.write_text("""
title: Test Rule
id: rule-008
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://example.com/test.md
""")

        written_files: list[Path] = []

        def write_on_download(url: str, output_path: Path, timeout: int = 30) -> bool:
            written_files.append(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("# content")
            return True

        db = _make_db()
        with (
            patch(
                "src.back.documents.sigma_ref_downloader._download_file",
                write_on_download,
            ),
            patch("time.sleep"),
        ):
            result = download_references(str(rules_dir), str(output_dir), db, request_delay=0)
            assert result["downloaded"] == 1
            entries = db.get_doc_sigma_ref()
            entry = list(entries)[0]
            assert "content_sha256" in entry
            assert entry["content_sha256"] != ""

    def test_content_changed_re_downloads(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        rule = rules_dir / "test_rule.yml"
        rule.write_text("""
title: Test Rule
id: rule-009
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://example.com/test.md
""")

        url_hash = _sha256("https://example.com/test.md")
        output_file = output_dir / f"{url_hash}.md"
        output_file.write_text("content on disk")

        db = _make_db(
            entries=[
                {
                    "url_hash": url_hash,
                    "original_url": "https://example.com/test.md",
                    "normalized_url": "https://example.com/test.md",
                    "content_type": "markdown",
                    "rule_id": "rule-009",
                    "title": "Test Rule",
                    "timestamp": iso_now(),
                    "content_sha256": "0000000000000000000000000000000000000000000000000000000000000000",
                }
            ]
        )

        download_calls: list[str] = []

        def tracking_download(url: str, output_path: Path, timeout: int = 30) -> bool:
            download_calls.append(url)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("new content")
            return True

        with (
            patch(
                "src.back.documents.sigma_ref_downloader._download_file",
                tracking_download,
            ),
            patch("time.sleep"),
        ):
            result = download_references(str(rules_dir), str(output_dir), db, request_delay=0)
            assert result["downloaded"] == 1
            assert len(download_calls) == 1

    def test_content_unchanged_skips(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        rule = rules_dir / "test_rule.yml"
        rule.write_text("""
title: Test Rule
id: rule-010
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://example.com/test.md
""")

        url_hash = _sha256("https://example.com/test.md")
        output_file = output_dir / f"{url_hash}.md"
        output_file.write_text("same content")
        same_sha = _sha256_file(output_file)

        db = _make_db(
            entries=[
                {
                    "url_hash": url_hash,
                    "original_url": "https://example.com/test.md",
                    "normalized_url": "https://example.com/test.md",
                    "content_type": "markdown",
                    "rule_id": "rule-010",
                    "title": "Test Rule",
                    "timestamp": iso_now(),
                    "content_sha256": same_sha,
                }
            ]
        )

        download_calls: list[str] = []

        def tracking_download(url: str, output_path: Path, timeout: int = 30) -> bool:
            download_calls.append(url)
            return True

        with (
            patch(
                "src.back.documents.sigma_ref_downloader._download_file",
                tracking_download,
            ),
        ):
            result = download_references(str(rules_dir), str(output_dir), db, request_delay=0)
            assert result["skipped"] >= 1
            assert len(download_calls) == 0

    def test_missing_content_sha256_skips(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        rule = rules_dir / "test_rule.yml"
        rule.write_text("""
title: Test Rule
id: rule-011
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://example.com/test.md
""")

        url_hash = _sha256("https://example.com/test.md")
        output_file = output_dir / f"{url_hash}.md"
        output_file.write_text("some content")

        db = _make_db(
            entries=[
                {
                    "url_hash": url_hash,
                    "original_url": "https://example.com/test.md",
                    "normalized_url": "https://example.com/test.md",
                    "content_type": "markdown",
                    "rule_id": "rule-011",
                    "title": "Test Rule",
                    "timestamp": iso_now(),
                }
            ]
        )

        download_calls: list[str] = []

        def tracking_download(url: str, output_path: Path, timeout: int = 30) -> bool:
            download_calls.append(url)
            return True

        with (
            patch(
                "src.back.documents.sigma_ref_downloader._download_file",
                tracking_download,
            ),
        ):
            result = download_references(str(rules_dir), str(output_dir), db, request_delay=0)
            assert result["skipped"] >= 1
            assert len(download_calls) == 0


class TestUppercaseScheme:
    def test_normalize_uppercase_http(self) -> None:
        url = "HTTP://example.com/doc.md"
        assert normalize_url(url) == "http://example.com/doc.md"

    def test_download_uppercase_scheme(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        output_dir = tmp_path / "output"
        rule = rules_dir / "test_rule.yml"
        rule.write_text("""
title: Test Rule
id: rule-012
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - HTTP://example.com/test.md
""")

        db = _make_db()
        with (
            patch(
                "src.back.documents.sigma_ref_downloader._download_file",
                return_value=True,
            ),
            patch("time.sleep"),
        ):
            result = download_references(str(rules_dir), str(output_dir), db, request_delay=0)
            assert result["downloaded"] == 1

    def test_uppercase_github_blob(self) -> None:
        url = "HTTP://GITHUB.COM/USER/REPO/BLOB/MAIN/DOC.MD"
        normalized = normalize_url(url)
        assert "raw.githubusercontent.com" in normalized.lower()
        assert normalized.startswith("https://")


class TestFragmentHandling:
    def test_github_url_with_fragment(self) -> None:
        url = "https://github.com/user/repo/blob/main/doc.md#section"
        assert normalize_url(url) == "https://raw.githubusercontent.com/user/repo/main/doc.md"

    def test_github_url_with_query_and_fragment(self) -> None:
        url = "https://github.com/user/repo/blob/main/doc.md?raw=true#section"
        result = normalize_url(url)
        assert result == "https://raw.githubusercontent.com/user/repo/main/doc.md"
        assert "?" not in result
        assert "#" not in result


class TestBackoffDelay:
    def test_first_attempt(self) -> None:
        assert _backoff_delay(1) == 1

    def test_second_attempt(self) -> None:
        assert _backoff_delay(2) == 4

    def test_third_attempt(self) -> None:
        assert _backoff_delay(3) == 9

    def test_beyond_list_length(self) -> None:
        assert _backoff_delay(4) == 9
        assert _backoff_delay(10) == 9


class TestGetRetryAfter:
    def test_no_header(self) -> None:
        response = MagicMock()
        response.headers = {}
        assert _get_retry_after(response) is None

    def test_valid_int(self) -> None:
        response = MagicMock()
        response.headers = {"Retry-After": "30"}
        assert _get_retry_after(response) == 30

    def test_invalid_value(self) -> None:
        response = MagicMock()
        response.headers = {"Retry-After": "not-a-number"}
        assert _get_retry_after(response) is None


class TestSha256File:
    def test_file_sha(self, tmp_path: Path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello")
        assert _sha256_file(f) == "2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824"

    def test_missing_file(self, tmp_path: Path) -> None:
        assert _sha256_file(tmp_path / "nonexistent") == ""


class TestConcurrencyLock:
    def test_lock_has_acquire_release(self) -> None:
        assert hasattr(_registry_lock, "acquire")
        assert hasattr(_registry_lock, "release")
