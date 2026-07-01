"""Tests for Sigma Specification API v1 endpoints."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from src.api.v1.documents.spec import router


@pytest.fixture
def client():
    """Create a test client with the spec router."""
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


class TestSpecReposEndpoint:
    """Tests for GET/POST /api/v1/spec/repos."""

    def test_list_repos_empty(self, client):
        """Test listing repos when none are registered."""
        with patch("src.api.v1.base.repo_router.list_repos", return_value=[]):
            response = client.get("/api/v1/spec/repos")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_repos_with_metadata(self, client):
        """Test listing repos with metadata."""
        with (
            patch(
                "src.api.v1.base.repo_router.list_repos",
                return_value=[{"org": "SigmaHQ", "name": "sigma-specification"}],
            ),
            patch(
                "src.api.v1.base.repo_router.get_metadata",
                return_value={"status": "synced", "branch": "main"},
            ),
            patch(
                "src.api.v1.base.repo_router.get_last_commit_date",
                return_value="2024-01-01T00:00:00",
            ),
        ):
            response = client.get("/api/v1/spec/repos")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["org"] == "SigmaHQ"
        assert data[0]["name"] == "sigma-specification"
        assert data[0]["sync_class"] == "btn-success"

    def test_add_repo_success(self, client, tmp_path):
        """Test adding a new repo."""
        repos_dir = tmp_path / "specification"
        repos_dir.mkdir()

        def mock_clone(url, repos_dir=None, branch=None):
            repo_dir = repos_dir / "SigmaHQ" / "sigma-specification"
            repo_dir.mkdir(parents=True, exist_ok=True)
            return {"success": True, "remote_head": "abc123"}

        with (
            patch("src.api.v1.base.repo_router.list_repos", return_value=[]),
            patch("src.api.v1.base.repo_router.clone_repo", side_effect=mock_clone),
            patch("src.api.v1.base.repo_router.save_metadata"),
            patch("src.api.v1.base.repo_router.save_selected_dirs"),
        ):
            response = client.post(
                "/api/v1/spec/repos",
                json={
                    "url": "https://github.com/SigmaHQ/sigma-specification.git",
                    "branch": "main",
                },
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Cloning" in data["message"]

    def test_add_repo_duplicate(self, client):
        """Test adding a duplicate repo."""
        with patch(
            "src.api.v1.base.repo_router.list_repos",
            return_value=[{"org": "sigmahq", "name": "sigma-specification"}],
        ):
            response = client.post(
                "/api/v1/spec/repos",
                json={"url": "https://github.com/SigmaHQ/sigma-specification.git"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "already exists" in data["error"]

    def test_delete_repo_success(self, client):
        """Test deleting a repo."""
        with patch("src.api.v1.base.repo_router.delete_repo", return_value={"success": True}):
            response = client.delete("/api/v1/spec/repos/SigmaHQ/sigma-specification")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_delete_repo_invalid_name(self, client):
        """Test deleting a repo with invalid characters in org name."""
        response = client.delete("/api/v1/spec/repos/S!ghQ/sigma-specification")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Invalid org/name" in data["error"]

    def test_sync_repo_success(self, client):
        """Test syncing a repo."""
        with (
            patch(
                "src.api.v1.base.repo_router.list_repos",
                return_value=[{"org": "SigmaHQ", "name": "sigma-specification"}],
            ),
            patch("src.api.v1.base.repo_router.get_metadata", return_value={"branch": "main"}),
        ):
            response = client.get("/api/v1/spec/repos/SigmaHQ/sigma-specification/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Sync started" in data["message"]

    def test_sync_repo_not_found(self, client):
        """Test syncing a non-existent repo."""
        with (
            patch("src.api.v1.base.repo_router.list_repos", return_value=[]),
            patch("src.api.v1.base.repo_router.get_metadata", return_value=None),
        ):
            response = client.get("/api/v1/spec/repos/SigmaHQ/nonexistent/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["error"].lower()

    def test_repo_tree_success(self, client, tmp_path):
        """Test getting repo directory tree."""
        repo_dir = tmp_path / "SigmaHQ" / "sigma-specification"
        repo_dir.mkdir(parents=True)
        (repo_dir / "rule-types").mkdir()

        def mock_tree(org, name, repos_dir=None, max_depth=None):
            return [{"name": "rule-types", "type": "dir", "path": "rule-types"}]

        repo_path = tmp_path / "SigmaHQ" / "sigma-specification"
        with (
            patch("src.api.v1.base.repo_router._get_repo_path", return_value=repo_path),
            patch("src.api.v1.base.repo_router._is_valid_repo", return_value=True),
            patch("src.api.v1.base.repo_router.list_directory_tree", side_effect=mock_tree),
        ):
            response = client.get("/api/v1/spec/repos/SigmaHQ/sigma-specification/tree")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["tree"]) == 1
        assert data["tree"][0]["name"] == "rule-types"

    def test_repo_tree_not_cloned(self, client):
        """Test getting tree for repo that isn't cloned yet."""
        with patch("src.api.v1.base.repo_router._get_repo_path", return_value=Path("/nonexistent")):
            response = client.get("/api/v1/spec/repos/SigmaHQ/sigma-specification/tree")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_select_dirs_success(self, client, tmp_path):
        """Test saving selected directories."""
        repo_dir = tmp_path / "SigmaHQ" / "sigma-specification"
        repo_dir.mkdir(parents=True)

        def mock_save(org, name, selected, repos_dir=None):
            return {"success": True}

        repo_path = tmp_path / "SigmaHQ" / "sigma-specification"
        with (
            patch("src.api.v1.base.repo_router._get_repo_path", return_value=repo_path),
            patch("src.api.v1.base.repo_router._is_valid_repo", return_value=True),
            patch(
                "src.api.v1.base.repo_router.save_selected_dirs", side_effect=mock_save
            ) as mock_save_dirs,
        ):
            response = client.post(
                "/api/v1/spec/repos/SigmaHQ/sigma-specification/select-dirs",
                json={"selected": ["rule-types"]},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        mock_save_dirs.assert_called_once()

    def test_sync_all_repos(self, client):
        """Test syncing all repos."""
        with patch(
            "src.api.v1.base.repo_router.list_repos",
            return_value=[{"org": "SigmaHQ", "name": "sigma-specification"}],
        ):
            response = client.post("/api/v1/spec/repos/sync-all")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
