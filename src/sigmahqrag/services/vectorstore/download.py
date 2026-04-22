"""Download Qdrant binary from GitHub releases."""

import logging
import os
import platform
import shutil
import subprocess
from pathlib import Path

from ...utils import download_file

logger = logging.getLogger(__name__)


def get_platform_info() -> dict[str, str]:
    """Get platform-specific information for Qdrant download."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        return {
            "system": "windows",
            "arch": "x86_64" if machine in ("amd64", "x86_64") else "aarch64",
            "extension": ".exe",
        }
    elif system == "darwin":
        return {
            "system": "darwin",
            "arch": "aarch64" if machine in ("arm64", "aarch64") else "x86_64",
            "extension": "",
        }
    elif system == "linux":
        return {
            "system": "linux",
            "arch": "x86_64" if machine in ("amd64", "x86_64") else "aarch64",
            "extension": "",
        }
    else:
        raise OSError(f"Unsupported platform: {system} {machine}")


def get_download_url(version: str = "latest") -> str:
    """Get the download URL for Qdrant binary."""
    platform_info = get_platform_info()

    base_url = "https://github.com/qdrant/qdrant/releases"

    if version == "latest":
        version_url = f"{base_url}/latest/download"
    else:
        version_url = f"{base_url}/download/{version}"

    filename = f"qdrant-{platform_info['system']}-{platform_info['arch']}"

    if platform_info["system"] == "windows":
        filename += ".exe"
    else:
        filename += ".tar.gz"

    return f"{version_url}/{filename}"


def download_qdrant(
    bin_dir: Path | None = None,
    version: str = "latest",
    force: bool = False,
) -> Path:
    """Download Qdrant binary to bin directory.

    Args:
        bin_dir: Directory to save the binary (default: "bin/")
        version: Version to download (default: "latest")
        force: Force re-download even if binary exists

    Returns:
        Path to the downloaded binary

    Raises:
        FileNotFoundError: If binary not found in archive
        OSError: If download or extraction fails
    """
    if bin_dir is None:
        bin_dir = Path("bin")

    platform_info = get_platform_info()
    binary_name = f"qdrant{platform_info['extension']}"
    binary_path = bin_dir / binary_name

    if binary_path.exists() and not force:
        logger.info(f"Binary already exists at {binary_path}")
        return binary_path

    try:
        if not bin_dir.exists():
            bin_dir.mkdir(parents=True)
    except OSError as e:
        raise OSError(f"Failed to create bin directory: {e}") from e

    url = get_download_url(version)
    logger.info(f"Downloading Qdrant from: {url}")

    temp_dir = bin_dir / "temp"
    temp_dir.mkdir(exist_ok=True)

    archive_path = temp_dir / url.split("/")[-1]

    try:
        try:
            download_file(url, archive_path)
        except OSError as e:
            raise OSError(f"Network error downloading Qdrant: {e}") from e

        logger.info(f"Downloaded to: {archive_path}")

        extracted_path: Path | None = None

        if platform_info["extension"] == ".exe":
            shutil.move(archive_path, binary_path)
        else:
            import tarfile

            with tarfile.open(archive_path, "r:gz") as tf:
                for member in tf.getmembers():
                    if "qdrant" in member.name and not member.name.endswith("/"):
                        tf.extract(member, temp_dir)
                        extracted_path = temp_dir / member.name
                        break

            if extracted_path is None:
                raise FileNotFoundError(
                    f"qdrant binary not found in archive {archive_path.name}. "
                    "Please check the release for the correct binary."
                )

            shutil.move(extracted_path, binary_path)

        if platform_info["system"] != "windows":
            os.chmod(binary_path, 0o755)

        logger.info(f"Binary saved to: {binary_path}")

    finally:
        try:
            if archive_path.exists():
                archive_path.unlink()
        except OSError:
            pass
        try:
            if temp_dir.exists():
                temp_dir.rmdir()
        except OSError:
            pass

    return binary_path


def get_binary_path(bin_dir: Path | None = None) -> Path:
    """Get the path to qdrant binary.

    Args:
        bin_dir: Custom bin directory (default: project root bin/)

    Returns:
        Path to the binary
    """
    if bin_dir is None:
        bin_dir = Path("bin")

    platform_info = get_platform_info()
    binary_name = f"qdrant{platform_info['extension']}"
    binary_path = bin_dir / binary_name

    if not binary_path.exists():
        raise FileNotFoundError(
            f"Qdrant binary not found at {binary_path}. Run download_qdrant() first."
        )

    return binary_path


def get_version(binary_path: Path | None = None) -> str:
    """Get Qdrant server version.

    Args:
        binary_path: Path to qdrant binary

    Returns:
        Version string

    Raises:
        RuntimeError: If binary is missing or version check fails
    """
    if binary_path is None:
        binary_path = get_binary_path()

    if not binary_path.exists():
        raise RuntimeError(f"Qdrant binary not found at {binary_path}")

    result = subprocess.run(
        [str(binary_path), "--version"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Version check failed (code {result.returncode}): {result.stderr}"
        )
    return result.stdout.strip()
