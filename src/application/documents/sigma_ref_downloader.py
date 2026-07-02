"""Download Sigma rule reference documents for offline RAG indexing."""

from __future__ import annotations

import logging
import threading
import urllib.parse
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, cast

import yaml

from src.shared.http import RETRY_STATUSES
from src.shared.http import download_file as http_download_file
from src.shared.http import head_url as http_head_url
from src.shared.utils.registry_utils import build_registry_entry
from src.shared.utils.crypto_utils import compute_sha256_file, compute_sha256_str
from src.shared.utils.identify_file_type import (
    SUPPORTED_DOC_EXTENSION_MAP,
    SUPPORTED_REFERENCE_DOC_TYPES,
)
from src.shared.utils.url_utils import is_private_url, normalize_url, url_ext
from src.infrastructure.database import DatabaseService
from src.core.sigma.models import is_sigma_rule_dict
from src.shared.utils import iso_now

logger = logging.getLogger(__name__)
DEFAULT_REQUEST_DELAY = 0.5
DEFAULT_MAX_WORKERS = 5
SUPPORTED_EXTENSIONS: dict[str, str] = {
    ext: ft.value for ext, ft in SUPPORTED_DOC_EXTENSION_MAP.items()
}

_registry_lock = threading.Lock()


def _detect_url_type(url: str, content_type: str | None = None) -> str | None:
    """Detect the document type of a reference URL.

    Checks URL extension first, then falls back to HTTP Content-Type.

    Args:
        url: The reference URL.
        content_type: Optional HTTP Content-Type header value.

    Returns:
        The FileType value string (e.g. "markdown") or None if unsupported.
    """
    parsed = urllib.parse.urlparse(url)
    path = parsed.path.rstrip("/")
    ext = Path(path).suffix.lower()

    if ext in SUPPORTED_EXTENSIONS:
        return SUPPORTED_EXTENSIONS[ext]

    if content_type:
        ct = content_type.lower()
        if ct.startswith("text/markdown"):
            return "markdown"
        if ct.startswith("text/html"):
            return "html"
        if ct.startswith("text/plain"):
            if ext in {".md", ".markdown"}:
                return "markdown"
            return "plain_text"
        if ct.startswith("application/pdf"):
            return "pdf"
        if ct.startswith("application/vnd.openxmlformats-officedocument"):
            return "office_document"
        if ct.startswith("application/vnd.oasis.opendocument"):
            return "office_document"
        if ct.startswith("application/msword"):
            return "office_document"
        if ct.startswith("application/rtf"):
            return "office_document"

    return None


def _load_registry(path: Path, db: DatabaseService) -> dict[str, Any]:
    """Load the registry from doc_registry for sigmaref org.

    Returns an empty dict if DB not available.
    """
    entries = db.get_entries_by_org("sigmaref", limit=0)
    registry = {}
    for entry in entries:
        url_hash = entry["url_hash"]
        registry[url_hash] = {
            "original_url": entry.get("original_url", ""),
            "normalized_url": entry.get("normalized_url"),
            "content_type": entry.get("content_type"),
            "rule_id": entry.get("rule_id"),
            "title": entry.get("title"),
            "timestamp": entry.get("timestamp"),
            "content_sha256": entry.get("content_sha256"),
            "embed_status": entry.get("embed_status"),
            "last_seen": entry.get("last_seen"),
            "file_name": entry.get("file_name", ""),
        }
    return registry


def _save_registry(registry: dict[str, Any], path: Path, db: DatabaseService) -> None:
    """Save the registry to doc_registry atomically in a single batch."""
    rows = []
    now = iso_now()
    for url_hash, entry in registry.items():
        if isinstance(entry, dict):
            rows.append(
                {
                    "url_hash": url_hash,
                    "original_url": entry.get("original_url", ""),
                    "normalized_url": entry.get("normalized_url"),
                    "content_type": entry.get("content_type"),
                    "rule_id": entry.get("rule_id"),
                    "title": entry.get("title"),
                    "timestamp": entry.get("timestamp"),
                    "content_sha256": entry.get("content_sha256"),
                    "org": entry.get("org", "sigmaref"),
                    "repo": entry.get("repo", "references"),
                    "file_name": entry.get("file_name", ""),
                    "file_size": entry.get("file_size"),
                    "embed_status": entry.get("embed_status", "discovery"),
                    "last_seen": entry.get("last_seen", now),
                }
            )
    db.batch_upsert_doc_registry(rows)


def _load_error_registry(db: DatabaseService) -> set[str]:
    """Load the set of url_hash values that have previously failed (30x/40x)."""
    try:
        entries = db.get_doc_errors()
        return {e["url_hash"] for e in entries}
    except Exception:
        logger.warning("Failed to load error registry from DuckDB — proceeding without it")
        return set()


def _maybe_record_error(
    db: DatabaseService,
    url_hash: str,
    original_url: str,
    normalized_url: str,
    status_code: int | None,
    rule_id: str,
    rule_title: str,
) -> None:
    """Record a 30x/40x download error in doc_error so it is skipped on retry."""
    if status_code is None:
        return
    if 300 <= status_code < 500 or (status_code >= 500 and status_code not in RETRY_STATUSES):
        try:
            db.upsert_doc_error(
                {
                    "url_hash": url_hash,
                    "original_url": original_url,
                    "normalized_url": normalized_url,
                    "error_code": status_code,
                    "error_message": f"HTTP {status_code}",
                    "org": "sigmaref",
                    "repo": "references",
                    "timestamp": iso_now(),
                }
            )
        except Exception:
            logger.warning("Failed to record error for %s", normalized_url)


def download_references(
    rules_dir: str,
    output_dir: str,
    db: DatabaseService,
    supported_types: set[str] | None = None,
    request_delay: float = DEFAULT_REQUEST_DELAY,
    progress_callback: Callable[[int, int, str], None] | None = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
    selected_dirs: list[str] | None = None,
) -> dict[str, Any]:
    """Download all Sigma rule references matching supported document types.

    Scans all Sigma rules in the given directory, extracts reference URLs,
    filters by supported document types, and downloads matching files.

    Args:
        rules_dir: Path to the directory containing Sigma rule YAML files.
        output_dir: Path to the output directory for downloaded files.
        db: Database service instance.
        supported_types: Set of FileType values to accept (e.g. {"markdown"}).
            Defaults to {"markdown"}.
        request_delay: Seconds to wait between download requests (sequential
            phase only; parallel phase uses max_workers instead).
        progress_callback: Optional callback(current, total) called after each file.
        max_workers: Max concurrent HTTP download threads.
        selected_dirs: Optional list of relative directory paths to scan.
            If provided, only files within these directories are processed.
            Directories not in this list are excluded from scanning.

    Returns:
        Dict with summary stats: total_rules, total_refs, downloaded, skipped, failed.
    """
    if supported_types is None:
        supported_types = SUPPORTED_REFERENCE_DOC_TYPES

    rules_path = Path(rules_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if not rules_path.is_dir():
        logger.warning("Rules directory does not exist: %s", rules_dir)
        return _empty_summary()

    with _registry_lock:
        registry = _load_registry(output_path, db)
        error_registry = _load_error_registry(db)

    total_rules = 0
    total_refs = 0
    downloaded = 0
    skipped = 0
    failed = 0

    _EXCLUDE_DIRS = {".github", ".git", "__pycache__", ".vscode", ".idea", ".pytest_cache"}

    def _is_selected_dir(yml_file: Path) -> bool:
        """Check if the file is within any of the selected directories."""
        if not selected_dirs:
            return True
        try:
            rel_path = yml_file.relative_to(rules_path).with_suffix("")
            rel_str = rel_path.as_posix()
            for sd in selected_dirs:
                clean_sd = sd.lstrip("./").rstrip("/")
                if not clean_sd:
                    return True
                if rel_str == clean_sd or rel_str.startswith(clean_sd + "/"):
                    return True
        except (ValueError, TypeError):
            pass
        return False

    def _collect_yaml_files() -> list[Path]:
        yml_files: list[Path] = []
        for pattern in ("*.yaml", "*.yml"):
            for yml_file in rules_path.rglob(pattern):
                parts = yml_file.parts
                if any(part in _EXCLUDE_DIRS for part in parts):
                    continue
                if not _is_selected_dir(yml_file):
                    continue
                yml_files.append(yml_file)
        return yml_files

    yml_files = _collect_yaml_files()

    # Phase 1: scan YAML files, classify refs
    download_queue: list[dict[str, Any]] = []
    head_pending: list[dict[str, Any]] = []

    total_files = len(yml_files)
    for file_idx, yml_file in enumerate(yml_files):
        if progress_callback:
            progress_callback(file_idx + 1, total_files, "scanning")
        if not yml_file.is_file():
            continue
        try:
            data = yaml.safe_load(yml_file.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            logger.warning("Failed to parse YAML %s: %s", yml_file, exc)
            continue
        if not isinstance(data, dict):
            continue
        if not is_sigma_rule_dict(data):
            continue

        total_rules += 1
        refs = data.get("references", [])
        if not isinstance(refs, list):
            continue

        rule_id = data.get("id", yml_file.stem)
        rule_title = data.get("title", "")

        for ref in refs:
            if not isinstance(ref, str):
                continue
            if not ref.lower().startswith(("http://", "https://")):
                logger.debug("Non-HTTP ref skipped: %s", ref)
                continue

            if is_private_url(ref):
                logger.warning("Skipping private URL ref: %s", ref)
                skipped += 1
                continue

            total_refs += 1
            normalized = normalize_url(ref)

            url_hash = compute_sha256_str(normalized)

            if url_hash in error_registry:
                logger.debug("Skipping previously failed URL: %s", normalized)
                skipped += 1
                continue

            # Fast path: already in registry with file_name and valid file on disk
            if url_hash in registry:
                fname = registry[url_hash].get("file_name", "")
                if fname:
                    output_file = output_path / fname
                    if output_file.exists():
                        existing_sha = registry[url_hash].get("content_sha256")
                        if (
                            existing_sha is not None
                            and compute_sha256_file(output_file) != existing_sha
                        ):
                            download_queue.append(
                                {
                                    "url_hash": url_hash,
                                    "original_url": ref,
                                    "normalized_url": normalized,
                                    "output_file": output_file,
                                    "content_type": registry[url_hash].get(
                                        "content_type", "markdown"
                                    ),
                                    "rule_id": rule_id,
                                    "rule_title": rule_title,
                                    "is_redownload": True,
                                }
                            )
                            continue
                        skipped += 1
                        continue
                # File missing or no file_name — fall through to re-download

            # Determine extension and content type
            ext = url_ext(normalized)
            ftype = _detect_url_type(normalized)
            if ftype is None and url_hash in registry:
                ct = registry[url_hash].get("content_type")
                if ct:
                    ftype = ct

            if ftype is None:
                head_pending.append(
                    {
                        "normalized": normalized,
                        "url_hash": url_hash,
                        "ext": ext,
                        "original_url": ref,
                        "rule_id": rule_id,
                        "rule_title": rule_title,
                    }
                )
                continue

            if not ext and ftype is not None:
                _TYPE_TO_EXT: dict[str, str] = {
                    "html": ".html",
                    "markdown": ".md",
                    "plain_text": ".txt",
                    "pdf": ".pdf",
                    "office_document": ".docx",
                }
                ext = _TYPE_TO_EXT.get(ftype, ".md")

            if not ext:
                ext = ".md"

            output_file = output_path / f"{url_hash}{ext}"

            if output_file.exists():
                content_hash = compute_sha256_file(output_file)
                if url_hash in registry:
                    existing_sha = registry[url_hash].get("content_sha256")
                    if existing_sha is not None and content_hash != existing_sha:
                        download_queue.append(
                            {
                                "url_hash": url_hash,
                                "original_url": ref,
                                "normalized_url": normalized,
                                "output_file": output_file,
                                "content_type": ftype or "markdown",
                                "rule_id": rule_id,
                                "rule_title": rule_title,
                                "is_redownload": True,
                            }
                        )
                        continue
                registry[url_hash] = build_registry_entry(
                    url_hash=url_hash,
                    original_url=ref,
                    normalized_url=normalized,
                    content_type=ftype or "markdown",
                    rule_id=rule_id,
                    title=rule_title,
                    content_sha256=content_hash,
                    file_name=output_file.name,
                    file_size=output_file.stat().st_size,
                )
                skipped += 1
                continue

            if ftype is None or ftype not in supported_types:
                skipped += 1
                continue

            download_queue.append(
                {
                    "url_hash": url_hash,
                    "original_url": ref,
                    "normalized_url": normalized,
                    "output_file": output_file,
                    "content_type": ftype,
                    "rule_id": rule_id,
                    "rule_title": rule_title,
                    "is_redownload": False,
                }
            )

    # Phase 1.5: batch HEAD requests in parallel for URLs with unknown type
    if head_pending:
        logger.info("Resolving %d unknown URL types via HEAD requests", len(head_pending))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map: dict[Future, dict[str, Any]] = {}
            for item in head_pending:
                future = executor.submit(http_head_url, item["normalized"], 10, check_ssrf=False)
                future_map[future] = item
            resolved = 0
            for future in as_completed(future_map):
                resolved += 1
                item = future_map[future]
                if progress_callback:
                    progress_callback(resolved, len(head_pending), "downloading")
                head_ct, _, _ = future.result()
                ftype = _detect_url_type(item["normalized"], content_type=head_ct)
                ext = item["ext"]
                if not ext and ftype is not None:
                    _TYPE_TO_EXT = {
                        "html": ".html",
                        "markdown": ".md",
                        "plain_text": ".txt",
                        "pdf": ".pdf",
                        "office_document": ".docx",
                    }
                    ext = _TYPE_TO_EXT.get(ftype, ".md")
                if not ext:
                    ext = ".md"
                output_file = output_path / f"{item['url_hash']}{ext}"
                if ftype is None or ftype not in supported_types:
                    skipped += 1
                    continue
                download_queue.append(
                    {
                        "url_hash": item["url_hash"],
                        "original_url": item["original_url"],
                        "normalized_url": item["normalized"],
                        "output_file": output_file,
                        "content_type": ftype,
                        "rule_id": item["rule_id"],
                        "rule_title": item["rule_title"],
                        "is_redownload": False,
                    }
                )

    # Phase 2: download all queued refs in parallel
    queue_size = len(download_queue)
    if download_queue:
        logger.info("Downloading %d refs with %d workers", queue_size, max_workers)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {}
            for item in download_queue:
                future = executor.submit(
                    http_download_file,
                    item["normalized_url"],
                    item["output_file"],
                    check_ssrf=False,
                )
                future_map[future] = item

            for idx, future in enumerate(as_completed(future_map)):
                if progress_callback:
                    progress_callback(idx + 1, queue_size, "downloading")
                item = future_map[future]
                success, status_code = cast(tuple[bool, int | None], future.result())
                if success:
                    output_file = item["output_file"]
                    content_hash = compute_sha256_file(output_file) if output_file.exists() else ""
                    registry[item["url_hash"]] = build_registry_entry(
                        url_hash=item["url_hash"],
                        original_url=item["original_url"],
                        normalized_url=item["normalized_url"],
                        content_type=item["content_type"],
                        rule_id=item["rule_id"],
                        title=item["rule_title"],
                        content_sha256=content_hash,
                        file_name=output_file.name,
                        file_size=output_file.stat().st_size if output_file.exists() else None,
                    )
                    downloaded += 1
                else:
                    _maybe_record_error(
                        db,
                        item["url_hash"],
                        item["original_url"],
                        item["normalized_url"],
                        status_code,
                        item["rule_id"],
                        item["rule_title"],
                    )
                    failed += 1

    with _registry_lock:
        _save_registry(registry, output_path, db)

    summary: dict[str, Any] = {
        "total_rules": total_rules,
        "total_refs": total_refs,
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
    }
    logger.info("Download complete: %s", summary)
    return summary


def _empty_summary() -> dict[str, Any]:
    """Return an empty summary dict."""
    return {
        "total_rules": 0,
        "total_refs": 0,
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
    }
