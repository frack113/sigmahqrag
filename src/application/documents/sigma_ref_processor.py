"""Process Sigma rules already in doc_registry and download their reference documents."""

from __future__ import annotations

import logging
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, cast

import httpx

from src.shared.utils.crypto_utils import compute_sha256_bytes
from src.shared.utils.identify_file_type import SUPPORTED_REFERENCE_DOC_TYPES
from src.shared.utils.sigma_utils import extract_sigma_references
from src.shared.utils.url_utils import is_private_url, normalize_url
from src.config.settings import get_config
from src.shared.utils import iso_now

logger = logging.getLogger(__name__)

DEFAULT_REQUEST_DELAY = 0.5
DEFAULT_MAX_WORKERS = 5


def _build_head_entry(
    normalized_url: str,
    content_type: str,
    rule_id: str,
    title: str,
    file_size: int | None = None,
) -> dict[str, Any]:
    now = iso_now()
    return {
        "url_hash": compute_sha256_bytes(normalized_url.encode()),
        "org": "sigmaref",
        "repo": "references",
        "content_type": content_type,
        "file_name": Path(normalized_url).name,
        "content_sha256": "",
        "file_size": file_size or 0,
        "original_url": normalized_url,
        "normalized_url": normalized_url,
        "rule_id": rule_id,
        "title": title,
        "timestamp": now,
        "last_seen": now,
        "embed_status": "head_verified",
    }


def _build_download_entry(
    normalized_url: str,
    content_type: str,
    rule_id: str,
    title: str,
    content_sha256: str,
    file_name: str = "",
    file_size: int | None = None,
) -> dict[str, Any]:
    """Build a doc_registry entry for a downloaded reference document."""
    now = iso_now()
    return {
        "url_hash": compute_sha256_bytes(normalized_url.encode()),
        "org": "sigmaref",
        "repo": "references",
        "content_type": content_type,
        "file_name": file_name or Path(normalized_url).name,
        "content_sha256": content_sha256,
        "file_size": file_size or 0,
        "original_url": normalized_url,
        "normalized_url": normalized_url,
        "rule_id": rule_id,
        "title": title,
        "timestamp": now,
        "last_seen": now,
        "embed_status": "discovery",
    }


def process_sigma_refs(
    db: Any,
    output_dir: str,
    supported_types: set[str] | None = None,
    request_delay: float = DEFAULT_REQUEST_DELAY,
    progress_callback: Callable[[int, int, str], None] | None = None,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> dict[str, Any]:
    """Process Sigma rules already in doc_registry and download their references.

    Parameters
    ----------
    db : DatabaseService
        Database service for writing registry entries.
    output_dir : str
        Directory where downloaded reference files are stored.
    supported_types : set[str] | None
        Allowed content types. Defaults to all reference doc types.
    request_delay : float
        Delay between sequential HEAD requests.
    progress_callback : callable | None
        ``progress_callback(current, total, phase)``.
    max_workers : int
        Max concurrent download threads.

    Returns
    -------
    dict
        Summary with keys: ``total_rules``, ``total_refs``, ``downloaded``,
        ``skipped``, ``failed``.
    """
    if supported_types is None:
        supported_types = SUPPORTED_REFERENCE_DOC_TYPES

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    entries = db.get_pending_registry_all()
    sigma_entries = [
        e
        for e in entries
        if e.get("content_type") == "sigma_rule" and e.get("embed_status") == "discovery"
    ]

    total_rules = len(sigma_entries)
    total_refs = 0
    downloaded = 0
    skipped = 0
    failed = 0

    head_queue: list[dict[str, Any]] = []  # needs HEAD + download
    download_ready: list[dict[str, Any]] = []  # has cached HEAD, needs download
    seen_urls: set[str] = set()  # deduplicate across rules within one run

    cfg = get_config()
    for rule_entry in sigma_entries:
        rule_id = rule_entry.get("rule_id", "00000000-0000-0000-0000-000000000000")
        original_url = rule_entry.get("original_url", "")
        file_name = rule_entry.get("file_name", "")

        # Resolve the actual file path from org/repo/file_name
        file_path = _resolve_rule_path(rule_entry, cfg)
        if not file_path or not file_path.exists():
            logger.warning("Rule file not found, skipping: %s (url=%s)", file_name, original_url)
            skipped += 1
            continue

        # Extract reference URLs from Sigma rule
        refs = extract_sigma_references(file_path)
        rule_title = rule_entry.get("title", file_name)
        logger.info("Rule %s processed: %d reference(s) found", rule_id, len(refs))

        if not refs:
            continue

        total_refs += len(refs)

        for ref_url in refs:
            ref_url_clean = ref_url.strip()
            if not ref_url_clean:
                continue

            norm_url = normalize_url(ref_url_clean)
            url_hash = compute_sha256_bytes(norm_url.encode())

            # Deduplicate within a single run (same URL across multiple rules)
            if url_hash in seen_urls:
                logger.debug("Reference already queued this run: %s", ref_url_clean)
                skipped += 1
                continue
            seen_urls.add(url_hash)

            existing = db.get_entry(url_hash)

            if existing and existing.get("content_sha256"):
                # Already fully downloaded
                logger.debug("Reference already registered: %s", ref_url_clean)
                skipped += 1
                continue

            base = {"url": ref_url_clean, "rule_id": rule_id, "rule_title": rule_title}
            if existing:
                # Cached HEAD result — skip HEAD, go straight to download
                download_ready.append(
                    {
                        **base,
                        "url_hash": url_hash,
                        "final_url": existing.get("normalized_url", ref_url_clean),
                        "content_type": existing.get("content_type", ""),
                    }
                )
            else:
                head_queue.append(base)

    total_head = len(head_queue)
    total_download_ready = len(download_ready)

    # Phase 1: Parallel HEAD requests to resolve content types
    head_pending: list[dict[str, Any]] = []
    head_completed = 0
    head_futures: dict[Future, dict[str, Any]] = {}

    total_head = len(head_queue)
    with ThreadPoolExecutor(max_workers=max_workers) as head_executor:
        for item in head_queue:
            future = head_executor.submit(_head_request, item["url"])
            head_futures[future] = item

        for future in as_completed(head_futures):
            head_completed += 1
            if progress_callback:
                progress_callback(
                    head_completed,
                    total_head + total_download_ready,
                    "resolving URLs",
                )

            item = head_futures[future]
            url = item["url"]
            try:
                content_type, size, final_url = future.result()
                norm_url = normalize_url(final_url or url)
                url_hash = compute_sha256_bytes(norm_url.encode())

                if content_type not in supported_types:
                    logger.info("Reference skipped (unsupported type): %s (%s)", url, content_type)
                    db.batch_upsert_doc_registry(
                        [
                            _build_head_entry(
                                normalized_url=norm_url,
                                content_type=content_type or "unknown",
                                rule_id=item["rule_id"],
                                title=item["rule_title"],
                            )
                        ]
                    )
                    skipped += 1
                    continue

                # Cache HEAD result immediately
                db.batch_upsert_doc_registry(
                    [
                        _build_head_entry(
                            normalized_url=norm_url,
                            content_type=content_type,
                            rule_id=item["rule_id"],
                            title=item["rule_title"],
                            file_size=size,
                        )
                    ]
                )
                head_pending.append(
                    {
                        **item,
                        "content_type": content_type,
                        "size": size,
                        "final_url": final_url or url,
                        "url_hash": url_hash,
                    }
                )
            except Exception as e:
                logger.warning("HEAD failed for %s: %s", url, e)
                failed += 1

    total_to_download = len(head_pending) + total_download_ready

    # Merge head_pending + download_ready (refs with cached HEAD)
    all_to_download = head_pending + download_ready

    # Phase 2: Parallel downloads
    def _download_one(item: dict[str, Any]) -> tuple[str, str, int] | None:
        url = item["final_url"]
        output_path = Path(output_dir)
        file_path = output_path / _sanitize_filename(url)

        if file_path.exists():
            url_hash = compute_sha256_bytes(url.encode())
            existing = db.get_entry(url_hash)
            if existing and existing.get("content_sha256"):
                logger.info("Reference already present: %s", url)
                return None

        try:
            with httpx.Client(
                timeout=httpx.Timeout(30.0), headers={"User-Agent": "SigmaRAG/1.0"}
            ) as client:
                resp = client.get(url)
                resp.raise_for_status()
                content = resp.content
            file_path.write_bytes(content)
            logger.info("Reference downloaded: %s", url)
            return ("ok", compute_sha256_bytes(content), len(content))
        except Exception as e:
            logger.error("Reference download failed: %s - %s", url, e)
            return ("fail", "", 0)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures: dict[Future, dict[str, Any]] = {
            executor.submit(_download_one, item): item for item in all_to_download
        }

        for future in as_completed(futures):
            item = futures[future]
            try:
                result = future.result()
                if result is None:
                    skipped += 1
                elif result[0] == "ok":
                    final_url = item["final_url"]
                    head_result = cast("tuple[str, str, int]", result)
                    entry = _build_download_entry(
                        normalized_url=final_url,
                        content_type=item["content_type"],
                        rule_id=item["rule_id"],
                        title=item["rule_title"],
                        content_sha256=head_result[1],
                        file_size=head_result[2],
                    )
                    db.batch_upsert_doc_registry([entry])
                    downloaded += 1
                else:
                    failed += 1
            except Exception as e:
                logger.error("Download task failed: %s", e)
                failed += 1

            if progress_callback:
                completed = downloaded + failed
                progress_callback(
                    total_head + completed,
                    total_head + total_to_download,
                    "downloading",
                )

    return {
        "total_rules": total_rules,
        "total_refs": total_refs,
        "downloaded": downloaded,
        "skipped": skipped,
        "failed": failed,
    }


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _resolve_rule_path(entry: dict, cfg: Any) -> Path | None:
    """Resolve the local file path for a sigma rule entry."""
    org = entry.get("org", "")
    repo = entry.get("repo", "")
    file_name = entry.get("file_name", "")

    if not file_name:
        return None

    if org == "local":
        base = Path(str(cfg.local_documents_path))
        return Path(base, file_name)

    if org == "sigmaref":
        base = Path(str(cfg.sigmaref_documents_path))
        return Path(base, file_name)

    if org and repo:
        base = Path(str(cfg.paths_github_dir))
        return Path(base, org, repo, file_name)

    return None


def _head_request(url: str, delay: float = 0.0) -> tuple[str | None, int | None, str | None]:
    """HEAD request to resolve content type and size."""
    if is_private_url(url):
        logger.warning("Skipping private URL: %s", url)
        return None, None, None
    try:
        with httpx.Client(
            timeout=httpx.Timeout(15.0), headers={"User-Agent": "SigmaRAG/1.0"}
        ) as client:
            resp = client.head(url, follow_redirects=True)
            resp.raise_for_status()
            ctype = resp.headers.get("content-type", "").split(";")[0].strip()
            size = int(resp.headers.get("content-length", 0))
            return ctype, size, str(resp.url)
    except Exception:
        return None, None, None


def _sanitize_filename(url: str) -> str:
    import re

    name = Path(url).name
    name = re.sub(r"[^a-zA-Z0-9._-]", "_", name)
    return name if name else "downloaded_file"
