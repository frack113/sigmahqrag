"""Shared URL normalization utilities."""

from __future__ import annotations

import ipaddress
import re
import urllib.parse
from pathlib import Path

_GITHUB_BLOB_PATTERN = re.compile(
    r"^https?://(?:www\.)?github\.com/([^/]+/[^/]+)/blob/([^#?]+)",
    re.IGNORECASE,
)


def normalize_url(url: str) -> str:
    """Normalize a reference URL for deduplication.

    Converts GitHub blob URLs to raw URLs, strips fragments,
    and removes refs/heads/ or refs/tags/ prefixes.
    """
    match = _GITHUB_BLOB_PATTERN.match(url)
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


def is_private_url(url: str) -> bool:
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


def url_ext(url: str) -> str:
    """Extract the file extension from a URL path."""
    parsed = urllib.parse.urlparse(url)
    return Path(parsed.path).suffix.lower()
