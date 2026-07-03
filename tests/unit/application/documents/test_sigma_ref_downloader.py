"""Tests for the Sigma reference downloader module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from src.shared.utils import iso_now
from src.shared.utils.crypto_utils import compute_sha256_file as _sha256_file
from src.shared.utils.crypto_utils import compute_sha256_str as _sha256
from src.shared.utils.identify_file_type import FILETYPE_TO_SUBDIR
from src.shared.utils.url_utils import is_private_url as _is_private_url, normalize_url

from src.application.documents.sigma_ref_downloader import (
    _detect_url_type,
    _load_registry,
    _registry_lock,
    _save_registry,
    download_references,
)


def _make_db(entries: list[dict] | None = None) -> MagicMock:
    """Create a mock DatabaseService with in-memory doc_registry."""

    data: dict[str, dict] = {}
    if entries:
        for e in entries:
            data[e["url_hash"]] = dict(e)

    def get_entries_by_org(org: str, limit: int = 100, offset: int = 0) -> list[dict]:
        return [
            {
                "url_hash": k,
                "org": v.get("org", org),
                "repo": v.get("repo", org),
                "original_url": v.get("original_url", ""),
                "normalized_url": v.get("normalized_url"),
                "content_type": v.get("content_type"),
                "rule_id": v.get("rule_id"),
                "title": v.get("title"),
                "timestamp": v.get("timestamp"),
                "content_sha256": v.get("content_sha256"),
                "embed_status": v.get("embed_status"),
                "file_name": v.get("file_name", ""),
                "file_size": v.get("file_size"),
            }
            for k, v in data.items()
        ]

    def upsert_doc_registry(entry: dict) -> None:
        data[entry["url_hash"]] = dict(entry)

    def batch_upsert_doc_registry(rows: list[dict]) -> None:
        for r in rows:
            data[r["url_hash"]] = dict(r)

    def get_doc_errors(limit: int = 1000, offset: int = 0) -> list[dict]:
        return []

    def upsert_doc_error(data_entry: dict) -> None:
        pass

    db = MagicMock()
    db.get_entries_by_org = get_entries_by_org
    db.upsert_doc_registry = upsert_doc_registry
    db.batch_upsert_doc_registry = batch_upsert_doc_registry
    db.get_doc_errors = get_doc_errors
    db.upsert_doc_error = upsert_doc_error
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
        assert _detect_url_type("https://example.com/doc.exe") is None

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
                "embed_status": None,
                "last_seen": None,
                "file_name": "",
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

    def test_save_sets_embed_status_discovery(self, tmp_path: Path) -> None:
        db = _make_db()
        data = {
            "abc": {
                "original_url": "https://example.com/doc.md",
                "timestamp": iso_now(),
            }
        }
        _save_registry(data, tmp_path, db)
        reg = _load_registry(tmp_path, db)
        assert reg["abc"]["embed_status"] == "discovery"

    def test_save_preserves_existing_embed_status(self, tmp_path: Path) -> None:
        db = _make_db()
        data = {
            "abc": {
                "original_url": "https://example.com/doc.md",
                "timestamp": iso_now(),
                "embed_status": "embedded",
            }
        }
        _save_registry(data, tmp_path, db)
        reg = _load_registry(tmp_path, db)
        assert reg["abc"]["embed_status"] == "embedded"


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
logsource:
  category: process_creation
  product: windows
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
            "src.application.documents.sigma_ref_downloader.http_download_file",
            return_value=(True, None),
        ):
            result = download_references(
                str(rules_dir), str(tmp_path / "output"), db, selected_dirs=[""]
            )
            assert result["downloaded"] == 1
            assert result["total_refs"] == 1

    def test_skip_unsupported_type(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        rule = rules_dir / "test_rule.yml"
        rule.write_text("""
title: Test Rule
id: rule-002
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://example.com/doc.exe
""")

        db = _make_db()
        result = download_references(
            str(rules_dir), str(tmp_path / "output"), db, selected_dirs=[""]
        )
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
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://example.com/doc.md
""")

        written_files: list[Path] = []

        def write_file(url: str, output_path: Path, **kwargs: object) -> tuple[bool, int | None]:
            written_files.append(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("# content")
            return True, None

        db = _make_db()
        with patch(
            "src.application.documents.sigma_ref_downloader.http_download_file",
            write_file,
        ):
            first = download_references(str(rules_dir), str(output_dir), db, selected_dirs=[""])
            assert first["downloaded"] == 1

            second = download_references(str(rules_dir), str(output_dir), db, selected_dirs=[""])
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
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://github.com/user/repo/blob/main/docs/guide.md
""")

        def check_normalized_url(
            url: str, output_path: Path, **kwargs: object
        ) -> tuple[bool, int | None]:
            assert "raw.githubusercontent.com" in url
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("# content")
            return True, None

        db = _make_db()
        with patch(
            "src.application.documents.sigma_ref_downloader.http_download_file",
            check_normalized_url,
        ):
            result = download_references(str(rules_dir), str(output_dir), db, selected_dirs=[""])
            assert result["downloaded"] == 1

            entries = db.get_entries_by_org("sigmaref")
            entry = entries[0]
            assert "raw.githubusercontent.com" in entry["normalized_url"]
            assert "/blob/" not in entry["normalized_url"]

    def test_empty_rules_dir(self, tmp_path: Path) -> None:
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        db = _make_db()
        result = download_references(
            str(empty_dir), str(tmp_path / "output"), db, selected_dirs=[""]
        )
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
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://example.com/test.md
""")

        db = _make_db()
        with patch(
            "src.application.documents.sigma_ref_downloader.http_download_file",
            return_value=(True, None),
        ):
            result = download_references(str(rules_dir), str(output_dir), db, selected_dirs=[""])
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
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://example.com/fail.md
""")

        db = _make_db()
        with patch(
            "src.application.documents.sigma_ref_downloader.http_download_file",
            return_value=(False, None),
        ):
            result = download_references(str(rules_dir), str(output_dir), db, selected_dirs=[""])
            assert result["failed"] == 1
            assert result["downloaded"] == 0
            assert len(db.get_entries_by_org("sigmaref")) == 0

    def test_same_filename_diff_content(self, tmp_path: Path) -> None:
        """Two different URLs with same filename -> stored under different hashes."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        output_dir = tmp_path / "output"
        rule = rules_dir / "test_rule.yml"
        rule.write_text("""
title: Test Rule
id: rule-007
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://example.com/a/readme.md
  - https://example.com/b/readme.md
""")

        urls_downloaded: list[str] = []

        def capture_url(url: str, output_path: Path, **kwargs: object) -> tuple[bool, int | None]:
            urls_downloaded.append(url)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("# content")
            return True, None

        db = _make_db()
        with patch(
            "src.application.documents.sigma_ref_downloader.http_download_file", capture_url
        ):
            result = download_references(str(rules_dir), str(output_dir), db, selected_dirs=[""])
            assert result["downloaded"] == 2
            assert len(urls_downloaded) == 2
            assert urls_downloaded[0] != urls_downloaded[1]

            assert len(db.get_entries_by_org("sigmaref")) == 2


class TestContentSha256:
    def test_registry_entry_includes_content_sha256(self, tmp_path: Path) -> None:
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        output_dir = tmp_path / "output"
        rule = rules_dir / "test_rule.yml"
        rule.write_text("""
title: Test Rule
id: rule-008
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - https://example.com/test.md
""")

        written_files: list[Path] = []

        def write_on_download(
            url: str, output_path: Path, **kwargs: object
        ) -> tuple[bool, int | None]:
            written_files.append(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("# content")
            return True, None

        db = _make_db()
        with (
            patch(
                "src.application.documents.sigma_ref_downloader.http_download_file",
                write_on_download,
            ),
            patch("time.sleep"),
        ):
            result = download_references(
                str(rules_dir), str(output_dir), db, selected_dirs=[""], request_delay=0
            )
            assert result["downloaded"] == 1
            entries = db.get_entries_by_org("sigmaref")
            entry = entries[0]
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
logsource:
  category: process_creation
  product: windows
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

        def tracking_download(
            url: str, output_path: Path, **kwargs: object
        ) -> tuple[bool, int | None]:
            download_calls.append(url)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("new content")
            return True, None

        with (
            patch(
                "src.application.documents.sigma_ref_downloader.http_download_file",
                tracking_download,
            ),
            patch("time.sleep"),
        ):
            result = download_references(
                str(rules_dir), str(output_dir), db, selected_dirs=[""], request_delay=0
            )
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
logsource:
  category: process_creation
  product: windows
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

        def tracking_download(
            url: str, output_path: Path, timeout: int = 30
        ) -> tuple[bool, int | None]:
            download_calls.append(url)
            return True, None

        with (
            patch(
                "src.application.documents.sigma_ref_downloader.http_download_file",
                tracking_download,
            ),
        ):
            result = download_references(
                str(rules_dir), str(output_dir), db, selected_dirs=[""], request_delay=0
            )
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
logsource:
  category: process_creation
  product: windows
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

        def tracking_download(
            url: str, output_path: Path, timeout: int = 30
        ) -> tuple[bool, int | None]:
            download_calls.append(url)
            return True, None

        with (
            patch(
                "src.application.documents.sigma_ref_downloader.http_download_file",
                tracking_download,
            ),
        ):
            result = download_references(
                str(rules_dir), str(output_dir), db, selected_dirs=[""], request_delay=0
            )
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
logsource:
  category: process_creation
  product: windows
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
                "src.application.documents.sigma_ref_downloader.http_download_file",
                return_value=(True, None),
            ),
            patch("time.sleep"),
        ):
            result = download_references(
                str(rules_dir), str(output_dir), db, selected_dirs=[""], request_delay=0
            )
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


class TestDownloadSigmaReferencesContract:
    """Contract tests: ``download_sigma_references`` with mode="scan" and
    mode="registry" must use the same ``{url_hash}{ext}`` naming convention
    for downloaded files.
    """

    def test_scan_mode_naming_convention(self, tmp_path: Path) -> None:
        """Scan mode downloads to ``{url_hash}.md``."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        output_dir = tmp_path / "output"
        ref_url = "https://example.com/test-doc.md"

        rule = rules_dir / "test_rule.yml"
        rule.write_text(f"""
title: Test Rule
id: contract-001
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - {ref_url}
""")

        expected_hash = _sha256(normalize_url(ref_url))
        expected_filename = f"{expected_hash}.md"

        def _fake_download(
            url: str, output_path: Path, **kwargs: object
        ) -> tuple[bool, int | None]:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("# test")
            return True, None

        db = _make_db()
        with patch(
            "src.application.documents.sigma_ref_downloader.http_download_file",
            _fake_download,
        ):
            from src.application.documents.sigma_ref_downloader import (
                download_sigma_references,
            )

            result = download_sigma_references(
                db=db,
                output_dir=str(output_dir),
                mode="scan",
                rules_dir=str(rules_dir),
            )

        assert result["downloaded"] == 1
        assert (output_dir / FILETYPE_TO_SUBDIR["markdown"] / expected_filename).exists()

    def test_registry_mode_runs_without_error(self, tmp_path: Path) -> None:
        """Registry mode runs without error (naming convention is inherited
        from the shared download helpers)."""
        output_dir = tmp_path / "output"
        output_dir.mkdir(parents=True)

        ref_url = "https://example.com/registry-doc.md"
        norm_url = normalize_url(ref_url)
        expected_hash = _sha256(norm_url)

        rule_file = tmp_path / "rule.yml"
        rule_file.write_text(f"""title: Registry Rule
id: contract-002
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - {ref_url}
""")

        db = MagicMock()
        db.get_pending_registry_all.return_value = [
            {
                "org": "local",
                "repo": "references",
                "file_name": "rule.yml",
                "rule_id": "contract-002",
                "original_url": "",
                "title": "Registry Rule",
                "content_type": "sigma_rule",
                "embed_status": "discovery",
                "url_hash": "dummy",
                "normalized_url": "",
            }
        ]
        db.get_entry.return_value = None
        db.batch_upsert_doc_registry = MagicMock()

        def _fake_download(
            url: str, output_path: Path, **kwargs: object
        ) -> tuple[bool, int | None]:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("# downloaded")
            return True, None

        with (
            patch(
                "src.application.documents.sigma_ref_downloader.get_config",
            ) as mock_cfg,
            patch(
                "src.application.documents.sigma_ref_downloader.http_head_url",
                return_value=("markdown", 1024, ref_url),
            ),
            patch(
                "src.application.documents.sigma_ref_downloader.http_download_file",
                _fake_download,
            ),
        ):
            from src.application.documents.sigma_ref_downloader import (
                download_sigma_references,
            )

            cfg = MagicMock()
            cfg.local_documents_path = str(tmp_path)
            cfg.sigmaref_documents_path = str(tmp_path)
            cfg.paths_github_dir = str(tmp_path)
            mock_cfg.return_value = cfg

            result = download_sigma_references(
                db=db,
                output_dir=str(output_dir),
                mode="registry",
            )

        assert result["total_rules"] == 1
        assert result["total_refs"] == 1
        # File should be written with {url_hash}{ext} naming
        expected_filename = f"{expected_hash}.md"
        assert (output_dir / FILETYPE_TO_SUBDIR["markdown"] / expected_filename).exists()


class TestRuleReferences:
    """Tests for rule↔reference tracking."""

    def test_scan_mode_populates_rule_references(self, tmp_path: Path) -> None:
        """Scan mode inserts rule_references rows via batch_upsert_rule_references."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        output_dir = tmp_path / "output"
        ref_url = "https://example.com/tracked-doc.md"

        rule = rules_dir / "test_rule.yml"
        rule.write_text(f"""
title: Tracked Rule
id: tracked-001
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - {ref_url}
""")

        db = _make_db()
        db.batch_upsert_rule_references = MagicMock()

        def _fake_download(
            url: str, output_path: Path, **kwargs: object
        ) -> tuple[bool, int | None]:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("# tracked")
            return True, None

        with patch(
            "src.application.documents.sigma_ref_downloader.http_download_file",
            _fake_download,
        ):
            from src.application.documents.sigma_ref_downloader import (
                download_sigma_references,
            )

            result = download_sigma_references(
                db=db,
                output_dir=str(output_dir),
                mode="scan",
                rules_dir=str(rules_dir),
            )

        assert result["downloaded"] == 1
        db.batch_upsert_rule_references.assert_called_once()
        args = db.batch_upsert_rule_references.call_args[0][0]
        assert len(args) == 1
        assert args[0]["rule_id"] == "tracked-001"
        assert args[0]["ref_url"] == ref_url

    def test_scan_mode_dedup_urls_in_rule_refs(self, tmp_path: Path) -> None:
        """Two rules referencing the same URL get two rule_references rows."""
        rules_dir = tmp_path / "rules"
        rules_dir.mkdir()
        output_dir = tmp_path / "output"
        ref_url = "https://example.com/shared-doc.md"

        rule_a = rules_dir / "rule_a.yml"
        rule_a.write_text(f"""
title: Rule A
id: rule-a
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    EventID: 4625
  condition: selection
references:
  - {ref_url}
""")

        rule_b = rules_dir / "rule_b.yml"
        rule_b.write_text(f"""
title: Rule B
id: rule-b
logsource:
  category: process_creation
  product: windows
detection:
  selection:
    EventID: 4688
  condition: selection
references:
  - {ref_url}
""")

        db = _make_db()
        db.batch_upsert_rule_references = MagicMock()

        def _fake_download(
            url: str, output_path: Path, **kwargs: object
        ) -> tuple[bool, int | None]:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text("# shared")
            return True, None

        with patch(
            "src.application.documents.sigma_ref_downloader.http_download_file",
            _fake_download,
        ):
            from src.application.documents.sigma_ref_downloader import (
                download_sigma_references,
            )

            download_sigma_references(
                db=db,
                output_dir=str(output_dir),
                mode="scan",
                rules_dir=str(rules_dir),
            )

        db.batch_upsert_rule_references.assert_called_once()
        rows = db.batch_upsert_rule_references.call_args[0][0]
        assert len(rows) == 2
        rule_ids = {r["rule_id"] for r in rows}
        assert rule_ids == {"rule-a", "rule-b"}
        assert rows[0]["url_hash"] == rows[1]["url_hash"]
