"""Tests for GitHub API v1 endpoints."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from src.api.v1.github import router
from src.back.github.git import list_repos, save_metadata, get_metadata, clone_repo, delete_repo, update_repo

@pytest.fixture
def client():
    """Create a test client with mocked dependencies."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)

class TestGitHubApiV1:
    """Tests for GET /api/v1/github endpoints."""

    def test_list_repos_empty(self, client):
        """Test listing repos when none exist."""
        with patch("src.api.v1.github.list_repos", return_value=[]):
            response = client.get("/api/v1/github/repos")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_repos_with_metadata(self, client):
        """Test listing repos with metadata."""
        mock_repos = [
            {"org": "test-org", "name": "test-repo", "path": "/tmp/test-org/test-repo", "branch": "main", "remote_url": "https://github.com/test-org/test-repo.git"}
        ]
        with patch("src.api.v1.github.list_repos", return_value=mock_repos), \
             patch("src.api.v1.github.get_metadata", return_value={"status": "synced", "last_synced": "2023-01-01T00:00:00"}), \
             patch("src.api.v1.github.is_repo_outdated", return_value=False), \
             patch("src.api.v1.github.get_last_commit_date", return_value="2023-01-01T00:00:00"):
            response = client.get("/api/v1/github/repos")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["org"] == "test-org"
        assert data[0]["name"] == "test-repo"
        assert data[0]["sync_class"] == "btn-success"

    def test_get_repo_not_found(self, client):
        """Test getting info for non-existent repo."""
        with patch("src.api.v1.github.list_repos", return_value=[]):
            response = client.get("/api/v1/github/repos/test-org/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_repo_success(self, client):
        """Test getting info for existing repo."""
        mock_repos = [{"org": "test-org", "name": "test-repo"}]
        with patch("src.api.v1.github.list_repos", return_value=mock_repos), \
             patch("src.api.v1.github.get_metadata", return_value={"status": "synced", "last_synced": "2023-01-01T00:00:00", "branch": "main"}):
            response = client.get("/api/v1/github/repos/test-org/test-repo")

        assert response.status_code == 200
        data = response.json()
        assert data["org"] == "test-org"
        assert data["name"] == "test-repo"
        assert data["repo_status"] == "synced"

class TestGitHubApiV1Post:
    """Tests for POST /api/v1/github endpoints."""

    @patch("src.api.v1.github.clone_repo")
    def test_add_repo_success(self, mock_clone, client):
        """Test successful repo addition (background task)."""
        mock_clone.return_value = {"success": True, "org": "test-org", "name": "test-repo", "path": "/tmp/test-org/test-repo"}
        
        payload = {"url": "https://github.com/test-org/test-repo.git", "branch": "main"}
        response = client.post("/api/v1/github/repos", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cloning" in data["message"].lower()

    @patch("src.api.v1.github.delete_repo")
    def test_delete_repo_success(self, mock_delete, client):
        """Test successful repo deletion."""
        mock_delete.return_value = {"success": True}
        
        response = client.delete("/api/v1/github/repos/test-org/test-repo")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("src.api.v1.git.list_directory_tree")
    def test_get_repo_tree(self, mock_tree, client):
        """Test getting directory tree."""
        mock_tree.return_value = [{"name": "folder", "path": "folder", "children": []}]
        with patch("src.api.v1.github.list_repos", return_value=[{"org": "test-org", "name": "test-repo"}]):
            response = client.get("/api/v1/github/repos/test-org/test-repo/tree")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tree"]) == 1
        assert data["tree"][0]["name"] == "folder"
