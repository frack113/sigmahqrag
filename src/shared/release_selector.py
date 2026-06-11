"""Generic GitHub release tag selector service.

Provides a reusable way to list releases for known services
(registered in VersionManager.SERVICE_REPOS) or arbitrary GitHub repos.
"""

from __future__ import annotations

import logging
from typing import Any

from src.infrastructure.github.api import list_releases
from src.shared.version_manager import VersionManager

logger = logging.getLogger(__name__)

SERVICE_REPOS_EXTENDED: dict[str, tuple[str, str]] = {
    **VersionManager.SERVICE_REPOS,
    "qdrant-web-ui": ("qdrant", "qdrant-web-ui"),
}


class ReleaseSelector:
    """Generic release tag selector for GitHub repositories.

    Supports both known services (registered in SERVICE_REPOS_EXTENDED)
    and arbitrary owner/repo pairs.
    """

    def __init__(self, github_token: str | None = None) -> None:
        self.github_token = github_token

    async def get_service_releases(self, service: str) -> list[dict[str, Any]]:
        """List all releases for a known service.

        Args:
            service: Service name key (e.g. 'llama.cpp', 'qdrant', 'qdrant-web-ui')

        Returns:
            List of release dicts with 'tag_name', 'name', 'published_at',
            'prerelease', 'draft', 'assets_count' keys.

        Raises:
            ValueError: If the service is not registered in SERVICE_REPOS_EXTENDED.
        """
        mapping = SERVICE_REPOS_EXTENDED.get(service)
        if mapping is None:
            known = list(SERVICE_REPOS_EXTENDED)
            raise ValueError(f"Unknown service '{service}'. Known services: {', '.join(known)}")
        owner, repo = mapping
        return await self.get_custom_releases(owner, repo)

    async def get_custom_releases(self, owner: str, repo: str) -> list[dict[str, Any]]:
        """List all releases for an arbitrary GitHub repository.

        Args:
            owner: GitHub owner (user or organization).
            repo: Repository name.

        Returns:
            List of release dicts (same shape as get_service_releases).
        """
        return await list_releases(owner, repo, self.github_token)


def create_release_selector(github_token: str | None = None) -> ReleaseSelector:
    """Factory for ReleaseSelector."""
    return ReleaseSelector(github_token=github_token)
