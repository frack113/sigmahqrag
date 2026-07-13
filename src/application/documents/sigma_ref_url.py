"""URL type detection for Sigma reference documents.

Detects the type of a URL based on its content type header or URL pattern.
"""

from __future__ import annotations

import logging
import re

from src.shared.utils.identify_file_type import (
    SUPPORTED_REFERENCE_DOC_TYPES,
    filetype_ext,
)
from src.shared.utils.url_utils import url_ext

logger = logging.getLogger(__name__)


def detect_url_type(url: str, content_type: str | None = None) -> str | None:
    """Detect the type of a URL.

    Args:
        url: The URL to detect.
        content_type: Optional content type from HEAD request.

    Returns:
        Detected file type string, or None if not supported.
    """
    # Try content type first
    if content_type:
        ctype = content_type.split(";")[0].strip().lower()
        if "markdown" in ctype:
            return "markdown"

    # Fall back to URL extension
    ext = url_ext(url)
    if ext:
        ext = ext.lower().lstrip(".")
        # Direct match against file type names (e.g. "markdown" -> "markdown")
        if ext in SUPPORTED_REFERENCE_DOC_TYPES:
            return ext
        # Map short extension to file type (e.g. "md" -> "markdown")
        for ft in SUPPORTED_REFERENCE_DOC_TYPES:
            if filetype_ext(ft).lstrip(".") == ext:
                return ft

    return None


def resolve_ext(url: str, ftype: str | None) -> str:
    """Resolve the file extension for a URL and content type.

    Args:
        url: The URL.
        ftype: Detected content type.

    Returns:
        File extension (e.g. ".md", ".pdf").
    """
    if ftype:
        ext = filetype_ext(ftype)
        if ext:
            return ext

    # Fall back to URL extension
    ext = url_ext(url)
    if ext:
        return ext

    return ".md"


# Pattern to match common reference URL patterns
REFERENCE_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("github_raw", re.compile(r"github\.com.*\/raw\/", re.IGNORECASE)),
    ("github_blob", re.compile(r"github\.com.*\/blob\/", re.IGNORECASE)),
    ("gitlab_raw", re.compile(r"gitlab\.com.*\/raw\/", re.IGNORECASE)),
    ("bitbucket", re.compile(r"bitbucket\.org.*\/raw\/", re.IGNORECASE)),
    ("rawcdn", re.compile(r"rawcdn\.com", re.IGNORECASE)),
    ("pastebin", re.compile(r"pastebin\.com", re.IGNORECASE)),
    ("hastebin", re.compile(r"hastebin\.com", re.IGNORECASE)),
    ("dpaste", re.compile(r"dpaste\.org", re.IGNORECASE)),
]


def is_reference_url(url: str) -> bool:
    """Check if a URL looks like a reference document URL.

    Args:
        url: URL to check.

    Returns:
        True if the URL matches reference patterns.
    """
    for _, pattern in REFERENCE_PATTERNS:
        if pattern.search(url):
            return True
    return False
