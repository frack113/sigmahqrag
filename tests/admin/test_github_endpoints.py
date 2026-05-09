"""Tests for GitHub admin endpoints."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from src.api.routes.admin_github import get_github_repo_manager, router
from src.git.repo_manager import RepositoryManager


@pytest.fixture
def github_repos_dir(tmp_path):
    """Create a temporary directory for GitHub repos."""
    repos_dir = tmp_path / "data" / "github"
    repos_dir.mkdir(parents=True)
    return repos_dir


@pytest.fixture
def repo_manager(github_repos_dir):
    """Create a RepositoryManager with temp directory."""
    return RepositoryManager(repos_dir=str(github_repos_dir))


@pytest.fixture
def client(repo_manager):
    """Create a test client with mocked dependencies."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)

    # Override the dependency
    async def mock_get_manager():
        return repo_manager

    app.dependency_overrides = {get_github_repo_manager: mock_get_manager}
    return TestClient(app)


class TestGitHubAdminGet:
    """Tests for GET /admin/github endpoint."""

    def test_list_repos_empty(self, client):
        """Test listing repos when none exist."""
        response = client.get("/admin/github?action=list")

        assert response.status_code == 200
        data = response.json()
        assert data["repos"] == []

    def test_list_repos_with_metadata(self, client, repo_manager, github_repos_dir):
        """Test listing repos with metadata."""
        org_name = "test-org"
        repo_name = "test-repo"
        repo_path = github_repos_dir / org_name / repo_name
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()

        metadata = {
            "org": org_name,
            "name": repo_name,
            "branch": "main",
            "extensions_to_index": ["*.yml"],
        }
        with open(repo_path / "metadata.json", "w") as f:
            json.dump(metadata, f)

        response = client.get("/admin/github?action=list")

        assert response.status_code == 200
        data = response.json()
        assert len(data["repos"]) == 1
        assert data["repos"][0]["org"] == org_name
        assert data["repos"][0]["name"] == repo_name
        assert data["repos"][0]["metadata"] == metadata

    def test_info_repo_not_found(self, client):
        """Test getting info for non-existent repo."""
        response = client.get("/admin/github?action=info&org=test-org&name=nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["error"].lower()

    def test_info_missing_params(self, client):
        """Test getting info with missing parameters."""
        response = client.get("/admin/github?action=info&name=test-repo")

        assert response.status_code == 400
        assert "required" in response.json()["error"].lower()

    def test_info_repo_without_metadata(self, client, github_repos_dir):
        """Test getting info for repo without metadata."""
        org_name = "test-org"
        repo_name = "test-repo"
        repo_path = github_repos_dir / org_name / repo_name
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()

        response = client.get(
            f"/admin/github?action=info&org={org_name}&name={repo_name}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["org"] == org_name
        assert data["name"] == repo_name
        assert data["metadata"] is None

    def test_info_repo_with_metadata(self, client, github_repos_dir):
        """Test getting info for repo with metadata."""
        org_name = "test-org"
        repo_name = "test-repo"
        repo_path = github_repos_dir / org_name / repo_name
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()

        metadata = {
            "org": org_name,
            "name": repo_name,
            "branch": "develop",
            "extensions_to_index": ["*.yml", "*.yaml"],
        }
        with open(repo_path / "metadata.json", "w") as f:
            json.dump(metadata, f)

        response = client.get(
            f"/admin/github?action=info&org={org_name}&name={repo_name}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"] == metadata

    def test_unknown_action(self, client):
        """Test with unknown action."""
        response = client.get("/admin/github?action=unknown")

        assert response.status_code == 400
        assert "Unknown action" in response.json()["error"]


class TestGitHubAdminPost:
    """Tests for POST /admin/github endpoint."""

    @patch("src.api.routes.admin_github.RepositoryManager.clone")
    def test_clone_success(self, mock_clone, client, github_repos_dir):
        """Test successful repo clone."""
        mock_clone.return_value = {
            "success": True,
            "org": "test-org",
            "name": "test-repo",
            "path": str(github_repos_dir / "test-org" / "test-repo"),
        }

        (github_repos_dir / "test-org").mkdir(exist_ok=True)

        response = client.post(
            "/admin/github?action=clone&org=test-org&name=test-repo&branch=main"
            "&extensions_to_index=*.yml&extensions_to_index=*.yaml"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cloned successfully" in data["message"].lower()

    def test_clone_missing_params(self, client):
        """Test clone with missing parameters."""
        # Missing org
        response = client.post("/admin/github?action=clone&name=test-repo&branch=main")
        assert response.status_code == 400
        assert "required" in response.json()["error"].lower()

        # Missing name
        response = client.post("/admin/github?action=clone&org=test-org&branch=main")
        assert response.status_code == 400
        assert "required" in response.json()["error"].lower()

        # Missing branch
        response = client.post("/admin/github?action=clone&org=test-org&name=test-repo")
        assert response.status_code == 400
        assert "required" in response.json()["error"].lower()

    @patch("src.api.routes.admin_github.RepositoryManager.clone")
    def test_clone_failure(self, mock_clone, client):
        """Test clone failure."""
        mock_clone.return_value = {
            "success": False,
            "error": "Repository already exists",
        }

        response = client.post(
            "/admin/github?action=clone&org=test-org&name=test-repo&branch=main"
        )

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    @patch("src.api.routes.admin_github.RepositoryManager.update")
    def test_update_success(self, mock_update, client):
        """Test successful repo update."""
        mock_update.return_value = {
            "success": True,
            "org": "test-org",
            "name": "test-repo",
            "path": "/some/path",
            "branch": "main",
        }

        response = client.post(
            "/admin/github?action=update&org=test-org&name=test-repo"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "updated successfully" in data["message"].lower()

    def test_update_missing_params(self, client):
        """Test update with missing parameters."""
        response = client.post("/admin/github?action=update&name=test-repo")

        assert response.status_code == 400
        assert "required" in response.json()["error"].lower()

    @patch("src.api.routes.admin_github.RepositoryManager.update")
    def test_update_failure(self, mock_update, client):
        """Test update failure."""
        mock_update.return_value = {
            "success": False,
            "error": "Repository not found",
        }

        response = client.post(
            "/admin/github?action=update&org=test-org&name=nonexistent"
        )

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    @patch("src.api.routes.admin_github.RepositoryManager.delete")
    def test_delete_success(self, mock_delete, client):
        """Test successful repo delete."""
        mock_delete.return_value = {"success": True}

        response = client.post(
            "/admin/github?action=delete&org=test-org&name=test-repo"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted" in data["message"].lower()

    def test_delete_missing_params(self, client):
        """Test delete with missing parameters."""
        response = client.post("/admin/github?action=delete&name=test-repo")

        assert response.status_code == 400
        assert "required" in response.json()["error"].lower()

    @patch("src.api.routes.admin_github.RepositoryManager.delete")
    def test_delete_failure(self, mock_delete, client):
        """Test delete failure."""
        mock_delete.return_value = {
            "success": False,
            "error": "Repository not found",
        }

        response = client.post(
            "/admin/github?action=delete&org=test-org&name=nonexistent"
        )

        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False

    def test_unknown_action(self, client):
        """Test with unknown action."""
        response = client.post("/admin/github?action=unknown")

        assert response.status_code == 400
        assert "Unknown action" in response.json()["error"]


class TestRepositoryManagerMetadata:
    """Tests for RepositoryManager metadata methods."""

    def test_save_and_get_metadata(self, repo_manager, github_repos_dir):
        """Test saving and retrieving metadata."""
        org_name = "test-org"
        repo_name = "test-repo"
        repo_path = github_repos_dir / org_name / repo_name
        repo_path.mkdir(parents=True)
        (repo_path / ".git").mkdir()

        metadata = {
            "org": org_name,
            "name": repo_name,
            "branch": "main",
            "extensions_to_index": ["*.yml", "*.yaml"],
        }

        repo_manager.save_metadata(org_name, repo_name, metadata)
        retrieved = repo_manager.get_metadata(org_name, repo_name)

        assert retrieved == metadata

    def test_get_metadata_not_exists(self, repo_manager):
        """Test getting metadata for non-existent repo."""
        result = repo_manager.get_metadata("nonexistent-org", "nonexistent-repo")
        assert result is None

    def test_list_with_metadata(self, repo_manager, github_repos_dir):
        """Test listing repos with metadata."""
        for org_name, repo_name in [("org1", "repo1"), ("org1", "repo2")]:
            repo_path = github_repos_dir / org_name / repo_name
            repo_path.mkdir(parents=True)
            (repo_path / ".git").mkdir()

            metadata = {
                "org": org_name,
                "name": repo_name,
                "branch": "main",
                "extensions_to_index": ["*.yml"],
            }
            repo_manager.save_metadata(org_name, repo_name, metadata)

        repos = repo_manager.list_with_metadata()

        assert len(repos) == 2
        assert all("metadata" in repo for repo in repos)
