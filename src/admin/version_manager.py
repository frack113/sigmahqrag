"""Version manager for GitHub releases API integration."""

from __future__ import annotations

import logging
import platform
import re
from dataclasses import dataclass

import httpx

from src.config import BIN_DIR

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
            r"llama-linux-x64",
            r"llama-linux-arm64",
            r"llama-macos-x64",
            r"llama-macos-arm64",
            r"llama-windows-x64",
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

    def _detect_platform(self) -> tuple[str, str]:
        """Detect current platform and architecture.

        Returns:
            Tuple of (os, arch)
        """
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

        return os_name, arch

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
        os_name, arch = self._detect_platform()
        patterns = self.BINARY_PATTERNS.get(service, [])

        for asset in release.assets:
            asset_name = asset.name.lower()

            if service == "llama.cpp":
                for pattern in patterns:
                    if os_name in pattern and arch in pattern:
                        if re.search(pattern, asset_name):
                            return asset
            elif service == "qdrant":
                for pattern in patterns:
                    if os_name in pattern or arch in pattern:
                        if re.search(pattern, asset_name):
                            return asset

            if os_name == "windows" and "windows" in asset_name:
                return asset
            if os_name == "macos" and "macos" in asset_name:
                return asset
            if os_name == "linux" and "linux" in asset_name:
                return asset

        logger.warning(
            f"No matching asset found for {service} on {os_name}-{arch}"
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
