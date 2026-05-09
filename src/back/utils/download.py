"""Download utilities."""

import logging
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger(__name__)


def download_file(url: str, dest_path: Path, timeout: int = 300) -> Path:
    """Download a file from URL to destination path.

    Args:
        url: URL to download from
        dest_path: Destination file path
        timeout: Download timeout in seconds

    Returns:
        Path to downloaded file

    Raises:
        OSError: If download fails
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Downloading {url}")

    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            with open(dest_path, "wb") as out_file:
                out_file.write(response.read())
    except urllib.error.URLError as e:
        raise OSError(f"Failed to download {url}: {e}") from e

    if not dest_path.exists():
        raise OSError(f"Download completed but file not found at {dest_path}")

    return dest_path
