"""Tests for system prompt management."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.core.system_prompt import _prompts, add_prompt
from src.main import create_app


@pytest.fixture
def tmp_prompts_file(tmp_path):
    """Fixture to provide a temporary prompts file."""
    temp_file = tmp_path / "test_system_prompt.toml"
    with patch("src.core.system_prompt.PROMPTS_FILE", temp_file):
        # Reset the singleton service to use the new path
        import src.core.system_prompt as sp

        sp._prompts_service = None
        sp._prompts.clear()
        yield temp_file


@pytest.fixture
def client(tmp_prompts_file) -> TestClient:
    """Create test client for the app."""
    app = create_app()
    return TestClient(app)


class TestSystemPromptAPI:
    """Tests for system prompt API routes."""

    def test_add_prompt(self, client, tmp_prompts_file) -> None:
        """Given a valid add request When POST /api/v1/admin/prompts Then returns 200 and creates prompt."""
        payload = {
            "name": "test-prompt",
            "content": "This is a test content.",
            "description": "This is a test description.",
        }
        response = client.post("/api/v1/admin/prompts", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["message"] == f"Prompt '{payload['name']}' saved"
        assert tmp_prompts_file.exists()

    def test_list_prompts(self, client, tmp_prompts_file) -> None:
        """Given existing prompts When GET /api/v1/admin/prompts Then returns list of prompts."""
        add_prompt("test-1", "desc1", "content1")

        response = client.get("/api/v1/admin/prompts")
        assert response.status_code == 200
        data = response.json()
        assert any(p["name"] == "test-1" for p in data)

    def test_get_prompt_by_id(self, client, tmp_prompts_file) -> None:
        """Given an existing prompt When GET /api/v1/admin/prompts/{id} Then returns content."""
        prompt = add_prompt("content-test", "desc", "secret content")

        response = client.get(f"/api/v1/admin/prompts/{prompt.id}")
        assert response.status_code == 200
        assert response.json()["content"] == "secret content"

    def test_get_prompt_by_name(self, client, tmp_prompts_file) -> None:
        """Given an existing prompt When GET /api/v1/admin/prompts/name/{name} Then returns content."""
        add_prompt("name-test", "desc", "secret content")

        response = client.get("/api/v1/admin/prompts/name/name-test")
        assert response.status_code == 200
        assert response.json()["content"] == "secret content"

    def test_update_prompt(self, client, tmp_prompts_file) -> None:
        """Given an existing prompt When PUT /api/v1/admin/prompts/{id} Then updates prompt."""
        new_prompt = add_prompt("to-update", "old desc", "old content")

        payload = {
            "name": "updated-name",
            "content": "updated content",
            "description": "updated description",
        }
        response = client.put(f"/api/v1/admin/prompts/{new_prompt.id}", json=payload)

        assert response.status_code == 200
        assert response.json()["message"] == f"Prompt '{new_prompt.id}' updated"

    def test_set_active_prompt(self, client, tmp_prompts_file) -> None:
        """Given prompts When POST /api/v1/prompts/activate/{id} Then sets prompt as active."""
        add_prompt("p1", "d1", "c1")
        p2 = add_prompt("p2", "d2", "c2")

        response = client.post(f"/api/v1/admin/prompts/activate/{p2.id}")
        assert response.status_code == 200
        assert response.json()["message"] == f"Prompt '{p2.name}' activated"

        from src.core.system_prompt import get_active_prompt

        active = get_active_prompt()
        assert active.id == p2.id

    def test_delete_prompt_by_id(self, client, tmp_prompts_file) -> None:
        """Given an existing prompt When DELETE /api/v1/admin/prompts/{id} Then deletes it."""
        prompt = add_prompt("to-delete", "desc", "content")

        response = client.delete(f"/api/v1/admin/prompts/{prompt.id}")
        assert response.status_code == 200
        assert response.json()["message"] == f"Prompt '{prompt.id}' deleted"

        assert prompt.id not in _prompts
