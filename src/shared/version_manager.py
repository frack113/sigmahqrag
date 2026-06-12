"""Version manager for GitHub releases API integration."""

from __future__ import annotations

import logging
import platform
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

from src.config.settings import BIN_DIR

logger = logging.getLogger(__name__)


@dataclass
class ReleaseAsset:
    """Represents a release asset (binary)."""

    name: str
    browser_download_url: str
    size: int


@dataclass
class ReleaseInfo:
    """Represents a GitHub release."""

    tag_name: str
    assets: list[ReleaseAsset]


class VersionManager:
    """Manager for GitHub releases and version resolution."""

    GITHUB_API_URL = "https://api.github.com/repos"

    SERVICE_REPOS = {
        "llama.cpp": ("ggml-org", "llama.cpp"),
        "qdrant": ("qdrant", "qdrant"),
    }

    BINARY_PATTERNS = {
        "llama.cpp": [
            r"llama-.*-win-hip-radeon-x64",
            r"llama-.*-win-cuda-\d+\.\d+-x64",
            r"llama-.*-win-cpu-x64",
            r"llama-.*-win-vulkan-x64",
            r"llama-.*-win-sycl-x64",
            r"llama-.*-ubuntu-x64",
            r"llama-.*-ubuntu-arm64",
            r"llama-.*-macos-x64",
            r"llama-.*-macos-arm64",
        ],
        "qdrant": [
            r"x86_64-unknown-linux-musl",
            r"aarch64-unknown-linux-musl",
            r"x86_64-pc-windows-msvc",
        ],
    }

    def __init__(self, github_token: str | None = None) -> None:
        """Initialize version manager.

        Args:
            github_token: Optional GitHub token for API requests
        """
        self.github_token = github_token

    def _get_headers(self) -> dict[str, str]:
        """Get headers for GitHub API requests."""
        headers = {"Accept": "application/vnd.github+json"}
        if self.github_token:
            headers["Authorization"] = f"Bearer {self.github_token}"
        return headers

    def _detect_platform(self) -> tuple[str, str, str | None]:
        """Detect current platform and architecture.

        Returns:
            Tuple of (os, arch, preferred_gpu_type)
            preferred_gpu_type: None, "hip", "cuda", or "cpu"
        """
        # First try to read OS from config (user's choice)
        os_name = self._read_os_preference()

        # If no config, detect from system
        if not os_name:
            system = platform.system().lower()
            machine = platform.machine().lower()

            if system == "windows":
                os_name = "windows"
            elif system == "darwin":
                os_name = "macos"
            elif system == "linux":
                os_name = "linux"
            else:
                os_name = system

            if machine in ("x86_64", "amd64"):
                arch = "x64"
            elif machine in ("aarch64", "arm64"):
                arch = "arm64"
            else:
                arch = machine
        else:
            # Use config OS, detect architecture
            machine = platform.machine().lower()
            if machine in ("x86_64", "amd64"):
                arch = "x64"
            elif machine in ("aarch64", "arm64"):
                arch = "arm64"
            else:
                arch = machine

        # Read preferred GPU type from config file
        preferred_gpu_type = self._read_gpu_preference()

        logger.info(
            f"Platform detection result: os={os_name}, arch={arch}, gpu={preferred_gpu_type}"
        )

        return os_name, arch, preferred_gpu_type

    def _read_os_preference(self) -> str | None:
        """Read OS preference from config file.

        Returns:
            "windows", "linux", "macos", or None if not specified
        """
        try:
            from src.config.settings import get_config

            config = get_config()
            os_val = config.os
            if not os_val:
                os_val = "windows"
            logger.info(f"OS from config: {os_val}")
            return os_val
        except Exception as e:
            logger.error(f"Could not read OS preference from config: {e}")
            import traceback

            traceback.print_exc()
        return None

    def _read_gpu_preference(self) -> str | None:
        """Read GPU preference from config file.

        Returns:
            "hip", "cuda", "cpu", or None if not specified
        """
        try:
            from src.config.settings import get_config

            return get_config().gpu_type
        except Exception as e:
            logger.debug(f"Could not read GPU preference from config: {e}")
        return None

    async def get_release(self, service: str, version: str | None = None) -> ReleaseInfo:
        """Get release information for a service.

        Args:
            service: Service name (llama.cpp, qdrant)
            version: Version tag or "latest"

        Returns:
            ReleaseInfo with version and assets

        Raises:
            ValueError: If service not supported or release not found
        """
        if service not in self.SERVICE_REPOS:
            raise ValueError(f"Unsupported service: {service}")

        owner, repo = self.SERVICE_REPOS[service]

        if version == "latest" or not version:
            url = f"{self.GITHUB_API_URL}/{owner}/{repo}/releases/latest"
        else:
            url = f"{self.GITHUB_API_URL}/{owner}/{repo}/releases/tags/{version}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url, headers=self._get_headers())
            response.raise_for_status()
            data = response.json()

            assets = [
                ReleaseAsset(
                    name=asset["name"],
                    browser_download_url=asset["browser_download_url"],
                    size=asset["size"],
                )
                for asset in data.get("assets", [])
            ]

            return ReleaseInfo(
                tag_name=data.get("tag_name", ""),
                assets=assets,
            )

    def find_matching_asset(self, release: ReleaseInfo, service: str) -> ReleaseAsset | None:
        """Find the asset matching the current platform.

        Args:
            release: ReleaseInfo from GitHub API
            service: Service name

        Returns:
            Matching ReleaseAsset or None
        """
        os_name, arch, preferred_gpu = self._detect_platform()
        patterns = self.BINARY_PATTERNS.get(service, [])

        # Filter assets by service-specific patterns
        for asset in release.assets:
            asset_name = asset.name.lower()

            # Skip cudart-* packages - these are CUDA runtime redistributables (DLLs only)
            # The main llama.cpp CUDA builds are named like llama-*-cuda-*.zip and should be kept
            if asset_name.startswith("cudart-"):
                continue

            if service == "llama.cpp":
                # Determine GPU type this asset corresponds to (from its name)
                def _asset_gpu_type(name: str) -> str | None:
                    if "hip" in name:
                        return "hip"
                    if "cuda" in name:
                        return "cuda"
                    if "vulkan" in name:
                        return "vulkan"
                    if "sycl" in name:
                        return "sycl"
                    if "opencl" in name:
                        return "opencl"
                    if "cpu" in name:
                        return "cpu"
                    return None

                # Try pattern match
                for pattern in patterns:
                    if re.search(pattern, asset_name):
                        asset_gpu = _asset_gpu_type(asset_name)
                        # If GPU preference is set on Windows, only accept matching GPU type
                        if preferred_gpu and os_name == "windows":
                            if asset_gpu == preferred_gpu:
                                logger.info(
                                    f"Matched {preferred_gpu.upper()} pattern {pattern} for {asset.name} (from config)"
                                )
                                return asset
                        else:
                            logger.info(f"Matched pattern {pattern} for {asset.name}")
                            return asset

                # Fallback: check for OS+arch in asset name
                asset_gpu = _asset_gpu_type(asset_name)
                if os_name == "windows" and "win" in asset_name and arch in asset_name:
                    if preferred_gpu and asset_gpu == preferred_gpu:
                        return asset
                    elif preferred_gpu is None:
                        return asset
                elif (
                    os_name == "linux"
                    and ("linux" in asset_name or "ubuntu" in asset_name)
                    and arch in asset_name
                ):
                    return asset
                elif os_name == "macos" and "macos" in asset_name and arch in asset_name:
                    return asset

            elif service == "qdrant":
                # For Qdrant, prioritize OS-specific match
                logger.info(f"QDRANT: Looking for {os_name} asset, asset_name={asset_name}")

                if os_name == "windows":
                    # Look for windows-msvc first
                    for pattern in [r"x86_64-pc-windows-msvc"]:
                        if re.search(pattern, asset_name):
                            logger.info(
                                f"QDRANT: Matched Windows pattern '{pattern}' for asset '{asset.name}'"
                            )
                            return asset
                elif os_name == "linux":
                    for pattern in [
                        r"x86_64-unknown-linux-musl",
                        r"aarch64-unknown-linux-musl",
                    ]:
                        if re.search(pattern, asset_name):
                            logger.info(
                                f"QDRANT: Matched Linux pattern '{pattern}' for asset '{asset.name}'"
                            )
                            return asset
                elif os_name == "macos":
                    if "macos" in asset_name or "apple" in asset_name:
                        logger.info(f"QDRANT: Matched macOS pattern for asset '{asset.name}'")
                        return asset

                # Fallback: check for OS in asset name
                if os_name == "windows" and "windows" in asset_name:
                    return asset
                elif os_name == "linux" and "linux" in asset_name:
                    return asset
                elif os_name == "macos" and "macos" in asset_name:
                    return asset

        logger.warning(
            f"No matching asset found for {service} on {os_name}-{arch} (GPU preference: {preferred_gpu})"
        )
        return None

    def get_binary_name(self, service: str, asset: ReleaseAsset) -> Path:
        """Get the target binary name for a service.

        Args:
            service: Service name
            asset: Release asset

        Returns:
            Target binary name
        """
        if service == "llama.cpp":
            return BIN_DIR / "llama-server"
        elif service == "qdrant":
            return BIN_DIR / "qdrant"

        return BIN_DIR / asset.name


def create_version_manager(github_token: str | None = None) -> VersionManager:
    """Create a version manager instance."""
    return VersionManager(github_token=github_token)


def _detect_llama_server_binary() -> Path | None:
    """Find the llama-server executable in the expected location.

    Returns:
        Path to llama-server or None if not found
    """
    import sys

    from src.config.settings import get_config

    config = get_config()
    bin_dir = config.resolve_llamacpp_bin_path()

    if sys.platform == "win32":
        candidates = ("llama-server.exe", "llama-server")
    else:
        candidates = ("llama-server", "llama-server.exe")

    for name in candidates:
        candidate = bin_dir / name
        if candidate.is_file():
            return candidate
    return None


def _try_get_llama_version_from_binary() -> str | None:
    """Try to detect llama.cpp version by running the binary with --version.

    Returns:
        Version string like "b9277" or None if detection fails
    """
    import re
    import subprocess

    binary = _detect_llama_server_binary()
    if not binary:
        return None

    try:
        result = subprocess.run(
            [str(binary), "--version"],
            capture_output=True,
            text=True,
            timeout=10.0,
        )
        output = result.stdout + result.stderr

        # Try to find version in output (common format: "b1234" or "version: b1234")
        patterns = [
            r"\b(b\d+)\b",  # Matches b1234
            r"version[:\s]+(b\d+)",
            r"llama.cpp\s+(b\d+)",
            r"build\s+(b\d+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, output, re.IGNORECASE)
            if match:
                return match.group(1)

        # Try to find numeric version without 'b' prefix
        num_match = re.search(r"\b(\d{4,})\b", output)
        if num_match:
            return f"b{num_match.group(1)}"

        return None
    except Exception:
        return None


async def get_current_version(service: str) -> str | None:
    """Get currently installed version for a service.

    Args:
        service: Service name (llama.cpp, qdrant)

    Returns:
        Version string or None
    """
    from src.config.settings import get_config

    config = get_config()
    if service in ("llama", "llama.cpp"):
        version = config.llamacpp_version
        # If version is default "0" but binary exists, try to detect actual version
        if version == "0":
            binary = _detect_llama_server_binary()
            if binary:
                # Binary exists but version is unknown - try to detect it
                detected = _try_get_llama_version_from_binary()
                if detected:
                    # Update config with detected version
                    config.llamacpp_version = detected
                    config.save()
                    return detected
                # Couldn't detect exact version, but binary exists
                return "installed"
        return version
    elif service in ("qdrant", "qdrant_db"):
        return config.qdrant_version
    return None


async def check_for_updates(service: str) -> dict | None:
    """Check if a new version is available for a service.

    Args:
        service: Service name (llama.cpp, qdrant)

    Returns:
        Dict with current_version, latest_version, update_available keys or None if check fails
    """
    vm = VersionManager()

    current = await get_current_version(service)
    if not current:
        return None

    try:
        release = await vm.get_release(service, "latest")
        latest = release.tag_name.removeprefix("v") if release.tag_name else None

        if not latest:
            return None

        update_available = current != latest

        return {
            "current_version": current,
            "latest_version": latest,
            "update_available": update_available,
        }
    except Exception:
        return None
