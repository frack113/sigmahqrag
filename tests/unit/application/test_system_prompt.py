"""Tests for system prompt management."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

MOCK_PROMPTS = {
    "prompt-1": MagicMock(
        id="prompt-1", name="test-1", description="desc1", content="content1", is_active=False
    ),
    "prompt-2": MagicMock(
        id="prompt-2", name="test-2", description="desc2", content="content2", is_active=True
    ),
}


@pytest.fixture
def mock_db():
    """Mock DatabaseService."""
    from src.application.system.prompts import Prompt

    db = MagicMock()
    db.get_prompts.return_value = [
        {
            "id": "prompt-1",
            "name": "test-1",
            "description": "desc1",
            "content": "content1",
            "is_active": False,
        },
        {
            "id": "prompt-2",
            "name": "test-2",
            "description": "desc2",
            "content": "content2",
            "is_active": True,
        },
    ]
    db.upsert_prompt.return_value = None
    db.persist.return_value = None
    db.delete_prompt.return_value = None
    with patch("src.application.system.prompts.DatabaseService.get_instance", return_value=db):
        with patch("src.application.system.prompts._ensure_loaded"):
            import src.application.system.prompts as sp

            sp._prompts = {
                "prompt-1": Prompt(
                    prompt_id="prompt-1",
                    name="test-1",
                    description="desc1",
                    content="content1",
                    is_active=False,
                ),
                "prompt-2": Prompt(
                    prompt_id="prompt-2",
                    name="test-2",
                    description="desc2",
                    content="content2",
                    is_active=True,
                ),
            }
            yield sp


@pytest.fixture
def client(mock_db) -> TestClient:
    """Create test client for the app."""
    from src.main import create_app

    app = create_app()
    return TestClient(app)


class TestSystemPromptAPI:
    """Tests for system prompt API routes."""

    def test_list_prompts(self, client, mock_db) -> None:
        """Given existing prompts When GET /api/v1/admin/prompts Then returns list of prompts."""
        response = client.get("/api/v1/admin/prompts")
        assert response.status_code == 200
        data = response.json()
        assert any(p["name"] == "test-1" for p in data)

    def test_get_prompt_by_id(self, client, mock_db) -> None:
        """Given an existing prompt When GET /api/v1/admin/prompts/{id} Then returns content."""
        response = client.get("/api/v1/admin/prompts/prompt-1")
        assert response.status_code == 200
        assert response.json()["content"] == "content1"

    def test_get_prompt_by_name(self, client, mock_db) -> None:
        """Given an existing prompt When GET /api/v1/admin/prompts/name/{name} Then returns content."""
        response = client.get("/api/v1/admin/prompts/name/test-2")
        assert response.status_code == 200
        assert response.json()["content"] == "content2"

    def test_get_active_prompt(self, client, mock_db) -> None:
        """Given an active prompt When GET /api/v1/admin/prompts/active Then returns it."""
        response = client.get("/api/v1/admin/prompts/active")
        assert response.status_code == 200
        assert response.json()["name"] == "test-2"

    def test_activate_prompt(self, client, mock_db) -> None:
        """Given prompts When POST /api/v1/admin/prompts/activate/{id} Then sets prompt as active."""
        response = client.post("/api/v1/admin/prompts/activate/prompt-1")
        assert response.status_code == 200

    def test_delete_prompt(self, client, mock_db) -> None:
        """Given an existing prompt When DELETE /api/v1/admin/prompts/{id} Then deletes it."""
        response = client.delete("/api/v1/admin/prompts/prompt-1")
        assert response.status_code == 200

    def test_add_prompt(self, client, mock_db) -> None:
        """Given a valid add request When POST /api/v1/admin/prompts Then returns 200."""
        payload = {
            "name": "new-prompt",
            "content": "This is new content.",
            "description": "A new description.",
        }
        response = client.post("/api/v1/admin/prompts", json=payload)
        assert response.status_code == 200
