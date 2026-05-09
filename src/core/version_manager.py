"""Version manager for GitHub releases API integration."""

from __future__ import annotations

import logging
import platform
import re
from dataclasses import dataclass

import httpx

from src.share import BIN_DIR

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
            r"llama-.*-win-hip.*x64",
            r"llama-.*-win-cuda-\d+\.\d+-x64",
            r"llama-.*-win-cpu-x64",
            r"llama-.*-linux-x64",
            r"llama-.*-linux-arm64",
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
            from src.share import get_backend_os, load_config

            config = load_config()
            print(f"DEBUG: Full config: {config}")
            os_val = config.get("backend", {}).get("os")
            print(f"DEBUG: OS from backend config: {os_val}")
            if not os_val:
                os_val = get_backend_os()
                print(f"DEBUG: OS from get_backend_os: {os_val}")
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
            from src.share import get_backend_gpu_type

            return get_backend_gpu_type()
        except Exception as e:
            logger.debug(f"Could not read GPU preference from config: {e}")
        return None

    async def get_release(
        self, service: str, version: str | None = None
    ) -> ReleaseInfo:
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
            tag = version if version.startswith("v") else f"v{version}"
            url = f"{self.GITHUB_API_URL}/{owner}/{repo}/releases/tags/{tag}"

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

    def find_matching_asset(
        self, release: ReleaseInfo, service: str
    ) -> ReleaseAsset | None:
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

            # Skip CUDA/cuBLAS/cuDNN/cuDART runtime libraries - these are not the main binary
            if "cuda" in asset_name or "cudnn" in asset_name or "cublas" in asset_name:
                continue

            if service == "llama.cpp":
                # Try pattern match
                for pattern in patterns:
                    if re.search(pattern, asset_name):
                        # If GPU preference is set, prioritize matching type
                        if preferred_gpu and os_name == "windows":
                            if (
                                (preferred_gpu == "hip" and "hip" in asset_name)
                                or (preferred_gpu == "cuda" and "cuda" in asset_name)
                                or (
                                    preferred_gpu == "cpu"
                                    and "cpu" in asset_name
                                    and "hip" not in asset_name
                                    and "cuda" not in asset_name
                                )
                            ):
                                logger.info(
                                    f"Matched {preferred_gpu.upper()} pattern {pattern} for {asset.name} (from config)"
                                )
                                return asset
                        else:
                            logger.info(f"Matched pattern {pattern} for {asset.name}")
                            return asset

                # Fallback: check for OS+arch in asset name
                if os_name == "windows" and "win" in asset_name and arch in asset_name:
                    if preferred_gpu == "hip" and "hip" in asset_name:
                        return asset
                    elif preferred_gpu == "cuda" and "cuda" in asset_name:
                        return asset
                    elif preferred_gpu == "cpu" and "cpu" in asset_name:
                        return asset
                    elif preferred_gpu is None:
                        # No preference: default to CPU or first match
                        return asset
                elif (
                    os_name == "linux"
                    and ("linux" in asset_name or "ubuntu" in asset_name)
                    and arch in asset_name
                ):
                    return asset
                elif (
                    os_name == "macos" and "macos" in asset_name and arch in asset_name
                ):
                    return asset

            elif service == "qdrant":
                # For Qdrant, prioritize OS-specific match
                logger.info(
                    f"QDRANT: Looking for {os_name} asset, asset_name={asset_name}"
                )

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
                        logger.info(
                            f"QDRANT: Matched macOS pattern for asset '{asset.name}'"
                        )
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

    def get_binary_name(self, service: str, asset: ReleaseAsset) -> str:
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


async def get_current_version(service: str) -> str | None:
    """Get currently installed version for a service.

    Args:
        service: Service name (llama.cpp, qdrant)

    Returns:
        Version string or None
    """
    if service in ("llama", "llama.cpp"):
        from src.core.backend.llamacpp import get_version

        return get_version()
    elif service in ("qdrant", "qdrant_db"):
        from src.core.backend.qdrant import get_version

        return get_version()
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
        latest = release.tag_name.lstrip("v") if release.tag_name else None

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
