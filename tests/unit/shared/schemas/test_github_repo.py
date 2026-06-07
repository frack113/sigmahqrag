"""Tests for GitHub repository schemas."""

from src.infrastructure.github.models import (
    GitHubRepoCreate,
    GitHubRepoInfo,
    GitHubRepoMetadata,
    GitHubRepoResponse,
)


class TestGitHubRepoMetadata:
    def test_init_required(self) -> None:
        meta = GitHubRepoMetadata(org="my-org", name="my-repo")
        assert meta.org == "my-org"
        assert meta.name == "my-repo"
        assert meta.branch == "main"
        assert meta.extensions_to_index == ["*.yml", "*.yaml"]

    def test_init_custom(self) -> None:
        meta = GitHubRepoMetadata(
            org="org", name="repo", branch="develop", extensions_to_index=["*.md"]
        )
        assert meta.branch == "develop"
        assert meta.extensions_to_index == ["*.md"]


class TestGitHubRepoCreate:
    def test_init(self) -> None:
        req = GitHubRepoCreate(org="org", name="repo", url="https://github.com/org/repo.git")
        assert req.org == "org"
        assert req.name == "repo"
        assert req.url == "https://github.com/org/repo.git"
        assert req.branch == "main"


class TestGitHubRepoResponse:
    def test_success(self) -> None:
        resp = GitHubRepoResponse(success=True, message="Cloned")
        assert resp.success is True
        assert resp.message == "Cloned"
        assert resp.error is None

    def test_failure(self) -> None:
        resp = GitHubRepoResponse(success=False, error="Failed")
        assert resp.success is False
        assert resp.error == "Failed"


class TestGitHubRepoInfo:
    def test_init(self) -> None:
        info = GitHubRepoInfo(name="repo", path="/path/to/repo")
        assert info.name == "repo"
        assert info.path == "/path/to/repo"
        assert info.metadata is None
