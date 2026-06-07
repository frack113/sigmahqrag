import hashlib
import logging
from pathlib import Path

from src.shared.utils.identify_file_type import identify
from src.shared.utils import iso_now
from src.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class DiscoveryWorker(BaseWorker):
    """Base class for file-discovery workers with shared helpers."""

    def _compute_sha256(self, file_path: Path) -> tuple[str, int]:
        """Returns (content_hash, file_size) using streaming hash."""
        h = hashlib.sha256()
        size = 0
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(65536), b""):
                    h.update(chunk)
                    size += len(chunk)
            return h.hexdigest(), size
        except Exception:
            return "", 0

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
        rule_id: str = "00000000-0000-0000-0000-000000000000",
    ) -> dict:
        url_hash = hashlib.sha256(normalized_url.encode()).hexdigest()
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
