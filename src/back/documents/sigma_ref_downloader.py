"""Download Sigma rule reference documents for offline RAG indexing."""

from __future__ import annotations

import ipaddress
import logging
import re
import threading
import time
import urllib.parse
from pathlib import Path
from typing import Any

import httpx
import yaml

from src.back.database import DatabaseService
from src.back.utils.identify_file_type import SUPPORTED_DOC_EXTENSION_MAP
from src.shared.utils import iso_now

logger = logging.getLogger(__name__)


def _is_private_url(url: str) -> bool:
    """Check if a URL points to a private/reserved IP to prevent SSRF."""
    parsed = urllib.parse.urlparse(url)
    host = parsed.hostname or ""
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    try:
        ip = ipaddress.ip_address(host)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


GITHUB_BLOB_PATTERN = re.compile(
    r"^https?://(?:www\.)?github\.com/([^/]+/[^/]+)/blob/([^#?]+)",
    re.IGNORECASE,
)
MAX_RETRIES = 3
BACKOFF_DELAYS = [1, 4, 9]
RETRY_STATUSES = {429, 500, 502, 503, 504}
DEFAULT_REQUEST_DELAY = 0.5
SUPPORTED_EXTENSIONS: dict[str, str] = {
    ext: ft.value for ext, ft in SUPPORTED_DOC_EXTENSION_MAP.items()
}

_registry_lock = threading.Lock()


def normalize_url(url: str) -> str:
    """Normalize a reference URL for deduplication."""
    match = GITHUB_BLOB_PATTERN.match(url)
    if match:
        repo = match.group(1)
        path_part = match.group(2)
        path_part = re.sub(r"^refs/heads/", "", path_part)
        path_part = re.sub(r"^refs/tags/", "", path_part)
        result = f"https://raw.githubusercontent.com/{repo}/{path_part}"
        parsed = urllib.parse.urlparse(result)
        if parsed.fragment:
            result = urllib.parse.urlunparse(parsed._replace(fragment=""))
        return result

    parsed = urllib.parse.urlparse(url)
    clean = parsed._replace(fragment="")
    return urllib.parse.urlunparse(clean)


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
        if ct.startswith("text/plain") and ext in {".md", ".markdown"}:
            return "markdown"

    return None


def _download_file(
    url: str,
    output_path: Path,
    timeout: int = 30,
    max_retries: int = MAX_RETRIES,
) -> bool:
    """Download a single file with retry and exponential backoff.

    Args:
        url: The URL to download.
        output_path: Local filesystem path to save the file.
        timeout: HTTP request timeout in seconds.
        max_retries: Maximum number of retry attempts. 0 means no retries.

    Returns:
        True if download succeeded, False otherwise.
    """
    for attempt in range(1, max_retries + 1):
        try:
            with httpx.Client(timeout=httpx.Timeout(timeout), follow_redirects=True) as client:
                response = client.get(url)
                response.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(response.content)
            return True

        except OSError as exc:
            logger.warning("Filesystem error for %s: %s — skipping", url, exc)
            if output_path.exists():
                try:
                    output_path.unlink()
                except OSError:
                    pass
            return False

        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            if status in RETRY_STATUSES and attempt < max_retries:
                retry_after = _get_retry_after(exc.response)
                if retry_after is not None:
                    wait: float = min(retry_after, 120)
                else:
                    wait = _backoff_delay(attempt)
                logger.warning(
                    "HTTP %d on attempt %d/%d for %s — waiting %ds",
                    status,
                    attempt,
                    max_retries,
                    url,
                    wait,
                )
                time.sleep(wait)
                continue
            logger.warning("HTTP %d for %s — giving up", status, url)
            return False

        except (httpx.TimeoutException, httpx.NetworkError, httpx.ConnectError) as exc:
            if attempt < max_retries:
                wait: float = _backoff_delay(attempt)  # type: ignore[no-redef]
                logger.warning(
                    "Network error on attempt %d/%d for %s: %s — waiting %ds",
                    attempt,
                    max_retries,
                    url,
                    exc,
                    wait,
                )
                time.sleep(wait)
                continue
            logger.warning("Network error for %s after %d attempts: %s", url, max_retries, exc)
            return False

    return False


def _backoff_delay(attempt: int) -> float:
    """Return the backoff delay for the given attempt number (1-indexed).

    Falls back to the last configured delay value if attempt exceeds the list.
    """
    idx = attempt - 1
    if idx < len(BACKOFF_DELAYS):
        return BACKOFF_DELAYS[idx]
    return BACKOFF_DELAYS[-1]


def _get_retry_after(response: httpx.Response) -> int | None:
    """Extract Retry-After header value as seconds."""
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _load_registry(path: Path, db: DatabaseService) -> dict[str, Any]:
    """Load the registry from DuckDB.

    Returns an empty dict if DB not available.
    """
    entries = db.get_doc_sigma_ref()
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
        }
    return registry


def _save_registry(registry: dict[str, Any], path: Path, db: DatabaseService) -> None:
    """Save the registry to DuckDB atomically."""
    for url_hash, entry in registry.items():
        if isinstance(entry, dict):
            row = {
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
            }
            db.upsert_doc_sigma_ref(row)


def _make_entry(
    url_hash: str,
    original_url: str,
    normalized_url: str,
    content_type: str,
    rule_id: str,
    title: str,
    timestamp: str,
    content_sha256: str,
    file_name: str = "",
    file_size: int | None = None,
) -> dict[str, Any]:
    """Build a registry entry dict with all fields expected by _save_registry."""
    return {
        "original_url": original_url,
        "normalized_url": normalized_url,
        "content_type": content_type,
        "rule_id": rule_id,
        "title": title,
        "timestamp": timestamp,
        "content_sha256": content_sha256,
        "org": "sigmaref",
        "repo": "references",
        "file_name": file_name,
        "file_size": file_size,
    }


def download_references(
    rules_dir: str,
    output_dir: str,
    db: DatabaseService,
    supported_types: set[str] | None = None,
    request_delay: float = DEFAULT_REQUEST_DELAY,
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
        request_delay: Seconds to wait between download requests.

    Returns:
        Dict with summary stats: total_rules, total_refs, downloaded, skipped, failed.
    """
    if supported_types is None:
        supported_types = {"markdown"}

    rules_path = Path(rules_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if not rules_path.is_dir():
        logger.warning("Rules directory does not exist: %s", rules_dir)
        return _empty_summary()

    with _registry_lock:
        registry = _load_registry(output_path, db)

    total_rules = 0
    total_refs = 0
    downloaded = 0
    skipped = 0
    failed = 0

    yml_patterns = ("*.yaml", "*.yml")
    yml_files: list[Path] = []
    for pattern in yml_patterns:
        yml_files.extend(rules_path.rglob(pattern))

    for yml_file in yml_files:
        if not yml_file.is_file():
            continue
        try:
            data = yaml.safe_load(yml_file.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:
            logger.warning("Failed to parse YAML %s: %s", yml_file, exc)
            continue
        if not isinstance(data, dict):
            logger.warning("YAML %s is not a dict, skipping", yml_file)
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

            if _is_private_url(ref):
                logger.warning("Skipping private URL ref: %s", ref)
                skipped += 1
                continue

            total_refs += 1
            normalized = normalize_url(ref)

            url_hash = _sha256(normalized)
            ext = _url_ext(normalized) or ".md"
            output_file = output_path / f"{url_hash}{ext}"

            if url_hash in registry:
                existing = registry[url_hash]
                if output_file.exists():
                    existing_sha = existing.get("content_sha256")
                    if existing_sha is not None and _sha256_file(output_file) != existing_sha:
                        logger.info("Content changed for %s, re-downloading", normalized)
                        if _download_file(normalized, output_file):
                            registry[url_hash] = _make_entry(
                                url_hash=url_hash,
                                original_url=ref,
                                normalized_url=normalized,
                                content_type=existing.get("content_type", "markdown"),
                                rule_id=rule_id,
                                title=rule_title,
                                timestamp=iso_now(),
                                content_sha256=_sha256_file(output_file),
                                file_name=output_file.name,
                                file_size=output_file.stat().st_size,
                            )
                            with _registry_lock:
                                _save_registry(registry, output_path, db)
                            downloaded += 1
                        else:
                            failed += 1
                        if request_delay > 0:
                            time.sleep(request_delay)
                        continue
                skipped += 1
                continue

            if output_file.exists():
                content_hash = _sha256_file(output_file)
                registry[url_hash] = _make_entry(
                    url_hash=url_hash,
                    original_url=ref,
                    normalized_url=normalized,
                    content_type=_detect_url_type(normalized) or "markdown",
                    rule_id=rule_id,
                    title=rule_title,
                    timestamp=iso_now(),
                    content_sha256=content_hash,
                    file_name=output_file.name,
                    file_size=output_file.stat().st_size,
                )
                with _registry_lock:
                    _save_registry(registry, output_path, db)
                skipped += 1
                continue

            ftype = _detect_url_type(normalized)
            if ftype is None or ftype not in supported_types:
                skipped += 1
                continue

            if _download_file(normalized, output_file):
                content_hash = _sha256_file(output_file) if output_file.exists() else ""
                registry[url_hash] = _make_entry(
                    url_hash=url_hash,
                    original_url=ref,
                    normalized_url=normalized,
                    content_type=ftype,
                    rule_id=rule_id,
                    title=rule_title,
                    timestamp=iso_now(),
                    content_sha256=content_hash,
                    file_name=output_file.name,
                    file_size=output_file.stat().st_size if output_file.exists() else None,
                )
                with _registry_lock:
                    _save_registry(registry, output_path, db)
                downloaded += 1
            else:
                failed += 1

            if request_delay > 0:
                time.sleep(request_delay)

    summary: dict[str, Any] = {
        "total_rules": total_rules,
        "total_refs": total_refs,
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
    }
    logger.info("Download complete: %s", summary)
    return summary


def _sha256(text: str) -> str:
    """Compute SHA256 hex digest of a string."""
    import hashlib

    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    """Compute SHA256 hex digest of a file's contents."""
    import hashlib

    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
    except OSError:
        return ""
    return h.hexdigest()


def _url_ext(url: str) -> str:
    """Extract the file extension from a URL path."""
    parsed = urllib.parse.urlparse(url)
    return Path(parsed.path).suffix.lower()


def _empty_summary() -> dict[str, Any]:
    """Return an empty summary dict."""
    return {
        "total_rules": 0,
        "total_refs": 0,
        "downloaded": 0,
        "skipped": 0,
        "failed": 0,
    }
