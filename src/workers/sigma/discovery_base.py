import logging
from pathlib import Path

from src.shared.constants import NULL_UUID
from src.shared.utils.crypto_utils import compute_sha256_file, compute_sha256_str
from src.shared.utils.identify_file_type import identify
from src.shared.utils import iso_now
from src.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class DiscoveryWorker(BaseWorker):
    """Base class for file-discovery workers with shared helpers."""

    def _compute_sha256(self, file_path: Path) -> tuple[str, int]:
        """Returns (content_hash, file_size) using streaming hash."""
        content_hash = compute_sha256_file(file_path)
        if not content_hash:
            return "", 0
        try:
            size = file_path.stat().st_size
        except OSError:
            size = 0
        return content_hash, size

    def _identify_content_type(self, file_path: Path) -> str:
        try:
            return identify(file_path).value
        except Exception:
            return "unknown"

    def _make_doc_registry_entry(
        self,
        org: str,
        repo: str,
        file_rel_path: str,
        content_type: str,
        content_hash: str,
        file_size: int,
        original_url: str,
        normalized_url: str,
        title: str,
        rule_id: str = NULL_UUID,
    ) -> dict:
        url_hash = compute_sha256_str(normalized_url)
        now = iso_now()
        return {
            "url_hash": url_hash,
            "org": org,
            "repo": repo,
            "content_type": content_type,
            "file_name": file_rel_path,
            "content_sha256": content_hash,
            "file_size": file_size,
            "original_url": original_url,
            "normalized_url": normalized_url,
            "rule_id": rule_id,
            "title": title,
            "timestamp": now,
            "last_seen": now,
            "embed_status": "discovery",
        }

    def _make_sigma_spec_entry(
        self,
        org: str,
        repo: str,
        file_rel_path: str,
        content_type: str,
        content_hash: str,
        file_size: int,
        original_url: str,
        normalized_url: str,
        title: str,
    ) -> dict:
        url_hash = compute_sha256_str(normalized_url)
        now = iso_now()
        return {
            "url_hash": url_hash,
            "org": org,
            "repo": repo,
            "content_type": content_type,
            "file_name": file_rel_path,
            "content_sha256": content_hash,
            "file_size": file_size,
            "original_url": original_url,
            "normalized_url": normalized_url,
            "title": title,
            "timestamp": now,
            "last_seen": now,
            "embed_status": "discovery",
        }
