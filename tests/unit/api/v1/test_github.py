"""Tests for GitHub API v1 endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.infrastructure.github import router


@pytest.fixture
def client():
    """Create a test client with mocked dependencies."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


class TestGitHubApiV1Get:
    """Tests for GET /api/v1/github endpoints."""

    def test_list_repos_empty(self, client):
        """Test listing repos when none exist."""
        with patch("src.api.v1.infrastructure.github.list_repos", return_value=[]):
            response = client.get("/api/v1/github/repos")

        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_list_repos_with_metadata_success(self, client):
        """Test listing repos with sync metadata and green badge."""
        mock_repos = [
            {
                "org": "test-org",
                "name": "test-repo",
                "path": "/tmp/test-org/test-repo",
                "branch": "main",
                "remote_url": "https://github.com/test-org/test-repo.git",
            }
        ]
        with (
            patch("src.api.v1.infrastructure.github.list_repos", return_value=mock_repos),
            patch(
                "src.api.v1.infrastructure.github.get_metadata",
                return_value={
                    "status": "synced",
                    "last_synced": datetime.now(timezone.utc).isoformat(),
                    "branch": "main",
                    "url": "https://github.com/test-org/test-repo.git",
                },
            ),
            patch("src.api.v1.infrastructure.github.is_repo_outdated", return_value=False),
            patch(
                "src.api.v1.infrastructure.github.get_last_commit_date",
                return_value=datetime.now(timezone.utc).isoformat(),
            ),
        ):
            response = client.get("/api/v1/github/repos")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["org"] == "test-org"
        assert data[0]["name"] == "test-repo"
        assert data[0]["branch"] == "main"
        assert data[0]["sync_class"] == "btn-success"

    def test_list_repos_with_metadata_outdated(self, client):
        """Test listing repos with outdated badge."""
        mock_repos = [
            {
                "org": "test-org",
                "name": "outdated-repo",
                "path": "/tmp/test-org/outdated-repo",
                "branch": "main",
                "remote_url": "https://github.com/test-org/outdated-repo.git",
            }
        ]
        with (
            patch("src.api.v1.infrastructure.github.list_repos", return_value=mock_repos),
            patch(
                "src.api.v1.infrastructure.github.get_metadata",
                return_value={
                    "status": "synced",
                    "last_synced": datetime.now(timezone.utc).isoformat(),
                    "branch": "main",
                },
            ),
            patch("src.api.v1.infrastructure.github.is_repo_outdated", return_value=True),
            patch(
                "src.api.v1.infrastructure.github.get_last_commit_date",
                return_value=datetime.now(timezone.utc).isoformat(),
            ),
        ):
            response = client.get("/api/v1/github/repos")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["sync_class"] == "btn-danger"

    def test_list_repos_with_metadata_cloning(self, client):
        """Test listing repos with cloning/warning status."""
        mock_repos = [
            {
                "org": "test-org",
                "name": "cloning-repo",
                "path": "/tmp/test-org/cloning-repo",
                "branch": "main",
            }
        ]
        with (
            patch("src.api.v1.infrastructure.github.list_repos", return_value=mock_repos),
            patch(
                "src.api.v1.infrastructure.github.get_metadata",
                return_value={
                    "status": "cloning",
                    "last_synced": datetime.now(timezone.utc).isoformat(),
                },
            ),
            patch(
                "src.api.v1.infrastructure.github.get_last_commit_date",
                return_value=datetime.now(timezone.utc).isoformat(),
            ),
        ):
            response = client.get("/api/v1/github/repos")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["sync_class"] == "btn-warning"

    def test_list_repos_with_metadata_error(self, client):
        """Test listing repos with error status."""
        mock_repos = [
            {
                "org": "test-org",
                "name": "error-repo",
                "path": "/tmp/test-org/error-repo",
                "branch": "main",
            }
        ]
        with (
            patch("src.api.v1.infrastructure.github.list_repos", return_value=mock_repos),
            patch(
                "src.api.v1.infrastructure.github.get_metadata",
                return_value={"status": "error", "error": "clone failed"},
            ),
            patch(
                "src.api.v1.infrastructure.github.get_last_commit_date",
                return_value=None,
            ),
        ):
            response = client.get("/api/v1/github/repos")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["sync_class"] == "btn-unknown"

    def test_get_repo_not_found(self, client):
        """Test getting info for non-existent repo."""
        with patch("src.api.v1.infrastructure.github.list_repos", return_value=[]):
            response = client.get("/api/v1/github/repos/test-org/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_repo_success(self, client):
        """Test getting info for existing repo."""
        mock_repos = [{"org": "test-org", "name": "test-repo"}]
        now_iso = datetime.now(timezone.utc).isoformat()
        with (
            patch("src.api.v1.infrastructure.github.list_repos", return_value=mock_repos),
            patch(
                "src.api.v1.infrastructure.github.get_metadata",
                return_value={
                    "status": "synced",
                    "last_synced": now_iso,
                    "branch": "main",
                    "url": "https://github.com/test-org/test-repo.git",
                },
            ),
            patch(
                "src.api.v1.infrastructure.github.get_last_commit_date",
                return_value=now_iso,
            ),
        ):
            response = client.get("/api/v1/github/repos/test-org/test-repo")

        assert response.status_code == 200
        data = response.json()
        assert data["org"] == "test-org"
        assert data["name"] == "test-repo"
        assert data["repo_status"] == "synced"
        assert data["branch"] == "main"

    def test_get_repo_error_status(self, client):
        """Test get repo returns error status correctly."""
        mock_repos = [{"org": "test-org", "name": "error-repo"}]
        with (
            patch("src.api.v1.infrastructure.github.list_repos", return_value=mock_repos),
            patch(
                "src.api.v1.infrastructure.github.get_metadata",
                return_value={"status": "error", "error": "clone failed"},
            ),
            patch("src.api.v1.infrastructure.github.get_last_commit_date", return_value=None),
        ):
            response = client.get("/api/v1/github/repos/test-org/error-repo")

        assert response.status_code == 200
        data = response.json()
        assert data["repo_status"] == "error"


class TestGitHubApiV1Post:
    """Tests for POST /api/v1/github endpoints."""

    @patch("src.api.v1.infrastructure.github.clone_repo")
    def test_add_repo_success(self, mock_clone, client):
        """Test successful repo addition (background task)."""
        mock_clone.return_value = {
            "success": True,
            "org": "test-org",
            "name": "test-repo",
            "path": "/tmp/test-org/test-repo",
            "remote_head": "abc123",
        }

        payload = {"url": "https://github.com/test-org/test-repo.git", "branch": "main"}
        response = client.post("/api/v1/github/repos", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "cloning" in data["message"].lower()

    @patch("src.api.v1.infrastructure.github.clone_repo")
    def test_add_repo_duplicate(self, mock_clone, client):
        """Test adding a repo that already exists."""
        with patch(
            "src.api.v1.infrastructure.github.list_repos",
            return_value=[{"org": "test-org", "name": "existing-repo"}],
        ):
            payload = {"url": "https://github.com/test-org/existing-repo.git", "branch": "main"}
            response = client.post("/api/v1/github/repos", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "already exists" in data["error"].lower()

    @patch("src.api.v1.infrastructure.github.clone_repo")
    def test_add_repo_invalid_url(self, mock_clone, client):
        """Test adding a repo with invalid URL format."""
        payload = {"url": "invalid-url", "branch": "main"}
        response = client.post("/api/v1/github/repos", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    @patch("src.api.v1.infrastructure.github.delete_repo")
    def test_delete_repo_success(self, mock_delete, client):
        """Test successful repo deletion."""
        mock_delete.return_value = {"success": True}

        response = client.delete("/api/v1/github/repos/test-org/test-repo")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @patch("src.api.v1.infrastructure.github.delete_repo")
    def test_delete_repo_failure(self, mock_delete, client):
        """Test failed repo deletion."""
        mock_delete.return_value = {"success": False, "error": "not found"}

        response = client.delete("/api/v1/github/repos/test-org/nonexistent")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_get_repo_tree(self, client):
        """Test getting directory tree."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True

        with (
            patch("src.api.v1.infrastructure.github._get_repo_path", return_value=mock_path),
            patch("src.api.v1.infrastructure.github._is_valid_repo", return_value=True),
            patch(
                "src.api.v1.infrastructure.github.get_metadata",
                return_value={"status": "synced"},
            ),
            patch("src.api.v1.infrastructure.github.get_selected_dirs", return_value=[]),
            patch(
                "src.api.v1.infrastructure.github.list_directory_tree",
                return_value=[{"name": "folder", "path": "folder", "children": []}],
            ),
        ):
            response = client.get("/api/v1/github/repos/test-org/test-repo/tree")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["tree"]) == 1
        assert data["tree"][0]["name"] == "folder"

    def test_get_repo_tree_not_found(self, client):
        """Test getting tree for a repo that doesn't exist."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False

        with patch("src.api.v1.infrastructure.github._get_repo_path", return_value=mock_path):
            response = client.get("/api/v1/github/repos/test-org/nonexistent/tree")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_get_repo_tree_path_traversal(self, client):
        """Test getting tree with path traversal in org name - FastAPI rejects invalid URL paths."""
        response = client.get("/api/v1/github/repos/../../etc/tree")

        # FastAPI rejects '..' segments at the routing level, returns 404 before handler runs
        assert response.status_code == 404

    def test_select_dirs_success(self, client):
        """Test saving selected directories."""
        mock_path = MagicMock()
        mock_path.exists.return_value = True

        payload = {"selected": ["folder1", "folder2"]}
        with (
            patch("src.api.v1.infrastructure.github._get_repo_path", return_value=mock_path),
            patch("src.api.v1.infrastructure.github._is_valid_repo", return_value=True),
            patch(
                "src.api.v1.infrastructure.github.save_selected_dirs",
                return_value={"success": True},
            ),
        ):
            response = client.post(
                "/api/v1/github/repos/test-org/test-repo/select-dirs", json=payload
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_select_dirs_repo_not_found(self, client):
        """Test saving selected dirs for a non-existent repo."""
        mock_path = MagicMock()
        mock_path.exists.return_value = False

        payload = {"selected": ["folder1"]}
        with patch("src.api.v1.infrastructure.github._get_repo_path", return_value=mock_path):
            response = client.post(
                "/api/v1/github/repos/test-org/nonexistent/select-dirs", json=payload
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False


class TestGitHubApiV1Sync:
    """Tests for sync endpoints."""

    def test_sync_repo_success(self, client):
        """Test successful repo sync."""
        with (
            patch(
                "src.api.v1.infrastructure.github.get_metadata",
                return_value={"status": "synced", "branch": "main"},
            ),
            patch(
                "src.api.v1.infrastructure.github.list_repos",
                return_value=[{"org": "test-org", "name": "test-repo"}],
            ),
            patch(
                "src.api.v1.infrastructure.github.update_repo",
                return_value={"success": True, "remote_head": "def456"},
            ),
        ):
            response = client.post("/api/v1/github/repos/test-org/test-repo/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "sync started" in data["message"].lower()

    def test_sync_repo_branch_override(self, client):
        """Test sync with explicit branch override."""
        with (
            patch("src.api.v1.infrastructure.github.get_metadata", return_value={"branch": "main"}),
            patch(
                "src.api.v1.infrastructure.github.list_repos",
                return_value=[{"org": "test-org", "name": "test-repo"}],
            ),
            patch("src.api.v1.infrastructure.github.update_repo", return_value={"success": True}),
        ):
            response = client.post("/api/v1/github/repos/test-org/test-repo/sync?branch=develop")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_sync_repo_not_found(self, client):
        """Test sync for non-existent repo."""
        with (
            patch("src.api.v1.infrastructure.github.get_metadata", return_value=None),
            patch(
                "src.api.v1.infrastructure.github.list_repos",
                return_value=[{"org": "other-org", "name": "other-repo"}],
            ),
        ):
            response = client.post("/api/v1/github/repos/test-org/nonexistent/sync")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False

    def test_sync_all_repos(self, client):
        """Test syncing all repos."""
        with (
            patch(
                "src.api.v1.infrastructure.github.list_repos",
                return_value=[
                    {"org": "test-org", "name": "repo-a"},
                    {"org": "test-org", "name": "repo-b"},
                ],
            ),
            patch("src.api.v1.infrastructure.github.get_metadata", return_value={"branch": "main"}),
            patch("src.api.v1.infrastructure.github.update_repo", return_value={"success": True}),
        ):
            response = client.post("/api/v1/github/repos/sync-all")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "sync started" in data["message"].lower()

    def test_sync_all_repos_empty(self, client):
        """Test syncing all repos when none exist."""
        with patch("src.api.v1.infrastructure.github.list_repos", return_value=[]):
            response = client.post("/api/v1/github/repos/sync-all")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "no repositories" in data["message"].lower()


class TestGitHubApiV1Status:
    """Tests for status endpoint."""

    def test_get_repo_status_existing(self, client):
        """Test getting status for an existing repo."""
        with (
            patch(
                "src.api.v1.infrastructure.github.list_repos",
                return_value=[{"org": "test-org", "name": "test-repo"}],
            ),
            patch(
                "src.api.v1.infrastructure.github.get_metadata",
                return_value={
                    "status": "synced",
                    "last_synced": datetime.now(timezone.utc).isoformat(),
                },
            ),
        ):
            response = client.get("/api/v1/github/repos/test-org/test-repo/status")

        assert response.status_code == 200
        data = response.json()
        assert data["org"] == "test-org"
        assert data["repo_status"] == "synced"

    def test_get_repo_status_not_cloned(self, client):
        """Test getting status for a repo in metadata but not cloned."""
        with patch(
            "src.api.v1.infrastructure.github.list_repos",
            return_value=[{"org": "test-org", "name": "cloned-repo"}],
        ):
            response = client.get("/api/v1/github/repos/test-org/not-cloned/status")

        assert response.status_code == 200
        data = response.json()
        assert data["repo_status"] == "error"


class TestGitHubApiV1Validation:
    """Tests for input validation."""

    def test_invalid_org_name_path_traversal(self, client):
        """Test that path traversal in org name is rejected by routing layer."""
        # FastAPI rejects '..' segments at the routing level before reaching any handler
        response = client.get("/api/v1/github/repos/../../../etc/passwd")

        assert response.status_code == 404

    def test_sync_repo_invalid_branch(self, client):
        """Test sync with branch containing path traversal."""
        with (
            patch("src.api.v1.infrastructure.github.get_metadata", return_value={"branch": "main"}),
            patch(
                "src.api.v1.infrastructure.github.list_repos",
                return_value=[{"org": "test-org", "name": "test-repo"}],
            ),
        ):
            response = client.post(
                "/api/v1/github/repos/test-org/test-repo/sync?branch=../etc/passwd"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "invalid branch" in data["error"].lower()

    def test_sync_repo_branch_too_long(self, client):
        """Test sync with excessively long branch name."""
        long_branch = "a" * 256

        with (
            patch("src.api.v1.infrastructure.github.get_metadata", return_value={"branch": "main"}),
            patch(
                "src.api.v1.infrastructure.github.list_repos",
                return_value=[{"org": "test-org", "name": "test-repo"}],
            ),
        ):
            response = client.post(
                f"/api/v1/github/repos/test-org/test-repo/sync?branch={long_branch}"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "too long" in data["error"].lower()


class TestGitHubApiV1ModelValidation:
    """Tests for Pydantic model validation."""

    def test_add_repo_missing_url(self, client):
        """Test adding a repo without URL (Pydantic validation error)."""
        payload = {"branch": "main"}
        response = client.post("/api/v1/github/repos", json=payload)

        assert response.status_code == 422

    def test_add_repo_branch_default(self, client):
        """Test that branch defaults to main."""
        with (
            patch(
                "src.api.v1.infrastructure.github.clone_repo",
                return_value={"success": True, "org": "x", "name": "y", "remote_head": ""},
            ),
            patch("src.api.v1.infrastructure.github.list_repos", return_value=[]),
        ):
            payload = {"url": "https://github.com/x/y.git"}
            response = client.post("/api/v1/github/repos", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestMarkSelected:
    """Tests for the _mark_selected helper."""

    def test_mark_selected_matches(self):
        """Test that matching nodes are marked as selected."""
        from src.api.v1.infrastructure.github import _mark_selected

        node = {
            "name": "folder",
            "path": "src/models",
            "children": [
                {"name": "sub", "path": "src/models/sub"},
            ],
        }
        _mark_selected(node, ["src/models"])
        assert node.get("selected") is True

    def test_mark_selected_nested_match(self):
        """Test matching on nested children."""
        from src.api.v1.infrastructure.github import _mark_selected

        node = {
            "name": "root",
            "path": "src",
            "children": [
                {"name": "sub", "path": "src/models"},
            ],
        }
        _mark_selected(node, ["src/models"])
        assert node.get("selected") is None  # parent not in selected list
        assert node["children"][0].get("selected") is True

    def test_mark_selected_no_match(self):
        """Test no marking when nothing matches."""
        from src.api.v1.infrastructure.github import _mark_selected

        node = {"name": "folder", "path": "src/models"}
        _mark_selected(node, ["other/path"])
        assert "selected" not in node
