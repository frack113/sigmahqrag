"""Tests for ReleaseSelector service."""

from unittest.mock import AsyncMock, patch

import pytest

from src.shared.release_selector import ReleaseSelector, SERVICE_REPOS_EXTENDED


def _mock_releases(tags: list[str]) -> list[dict]:
    return [
        {
            "tag_name": t,
            "name": f"Release {t}",
            "published_at": "2024-01-01T00:00:00Z",
            "prerelease": False,
            "draft": False,
            "assets_count": 1,
        }
        for t in tags
    ]


class TestReleaseSelector:
    @pytest.mark.asyncio
    async def test_get_service_releases_known(self):
        releases = _mock_releases(["v1.0.0", "v1.1.0"])
        with patch(
            "src.shared.release_selector.list_releases",
            new_callable=AsyncMock,
            return_value=releases,
        ) as mock_list:
            selector = ReleaseSelector()
            result = await selector.get_service_releases("llama.cpp")
            assert result == releases
            mock_list.assert_awaited_once_with("ggml-org", "llama.cpp", None)

    @pytest.mark.asyncio
    async def test_get_service_releases_qdrant_web_ui(self):
        releases = _mock_releases(["v0.2.11", "v0.3.0"])
        with patch(
            "src.shared.release_selector.list_releases",
            new_callable=AsyncMock,
            return_value=releases,
        ) as mock_list:
            selector = ReleaseSelector()
            result = await selector.get_service_releases("qdrant-web-ui")
            assert result == releases
            mock_list.assert_awaited_once_with("qdrant", "qdrant-web-ui", None)

    @pytest.mark.asyncio
    async def test_get_service_releases_unknown(self):
        selector = ReleaseSelector()
        with pytest.raises(ValueError, match="Unknown service"):
            await selector.get_service_releases("nonexistent")

    @pytest.mark.asyncio
    async def test_get_custom_releases(self):
        releases = _mock_releases(["v2.0.0"])
        with patch(
            "src.shared.release_selector.list_releases",
            new_callable=AsyncMock,
            return_value=releases,
        ) as mock_list:
            selector = ReleaseSelector(github_token="token-123")
            result = await selector.get_custom_releases("custom-owner", "custom-repo")
            assert result == releases
            mock_list.assert_awaited_once_with("custom-owner", "custom-repo", "token-123")

    def test_service_repos_extended_contains_all_expected(self):
        assert "llama.cpp" in SERVICE_REPOS_EXTENDED
        assert SERVICE_REPOS_EXTENDED["llama.cpp"] == ("ggml-org", "llama.cpp")
        assert "qdrant" in SERVICE_REPOS_EXTENDED
        assert SERVICE_REPOS_EXTENDED["qdrant"] == ("qdrant", "qdrant")
        assert "qdrant-web-ui" in SERVICE_REPOS_EXTENDED
        assert SERVICE_REPOS_EXTENDED["qdrant-web-ui"] == ("qdrant", "qdrant-web-ui")
