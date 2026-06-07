"""Tests for admin delete endpoints (models/delete, models/delete-embedding)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.models.admin_models import router as admin_router


@pytest.fixture
def app() -> FastAPI:
    test_app = FastAPI()
    test_app.include_router(admin_router)
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app)


# ── POST /api/v1/admin/models/delete ──────────────────────────────────────


PATCH_DB = "src.api.dependencies.get_database_service"
PATCH_REG = "src.api.dependencies.get_unified_registry"


class TestModelsDelete:
    @patch(PATCH_DB)
    @patch(PATCH_REG)
    def test_delete_file_calls_remove_llm_when_last_file(
        self, mock_get_reg: MagicMock, mock_get_db: MagicMock, client: TestClient
    ) -> None:
        reg = MagicMock()
        record = {
            "local_path": "/data/models/llm/org/m",
            "files": {
                "model.gguf": {
                    "filename": "model.gguf",
                    "local_path": "/data/models/llm/org/m/model.gguf",
                    "file_size": 100,
                }
            },
        }
        reg.get_llm.return_value = record
        mock_get_reg.return_value = reg

        with patch("src.config.settings.LLM_DIR", new="/data/models/llm"):
            response = client.post(
                "/api/v1/admin/models/delete",
                json={"repo_id": "org/m", "filename": "model.gguf"},
            )

        assert response.status_code == 200
        reg.remove_llm.assert_called_once_with("org/m", mock_get_db.return_value)
        reg._save.assert_not_called()

    @patch(PATCH_DB)
    @patch(PATCH_REG)
    def test_delete_file_calls_save_when_files_remain(
        self, mock_get_reg: MagicMock, mock_get_db: MagicMock, client: TestClient
    ) -> None:
        reg = MagicMock()
        record = {
            "local_path": "/data/models/llm/org/m",
            "files": {
                "model1.gguf": {
                    "filename": "model1.gguf",
                    "local_path": "/data/models/llm/org/m/model1.gguf",
                },
                "model2.gguf": {
                    "filename": "model2.gguf",
                    "local_path": "/data/models/llm/org/m/model2.gguf",
                },
            },
        }
        reg.get_llm.return_value = record
        mock_get_reg.return_value = reg

        with patch("src.config.settings.LLM_DIR", new="/data/models/llm"):
            response = client.post(
                "/api/v1/admin/models/delete",
                json={"repo_id": "org/m", "filename": "model1.gguf"},
            )

        assert response.status_code == 200
        reg._save.assert_called_once()
        reg.remove_llm.assert_not_called()

    @patch(PATCH_DB)
    @patch(PATCH_REG)
    def test_delete_file_missing_returns_404(
        self, mock_get_reg: MagicMock, mock_get_db: MagicMock, client: TestClient
    ) -> None:
        reg = MagicMock()
        reg.get_llm.return_value = None
        mock_get_reg.return_value = reg

        response = client.post(
            "/api/v1/admin/models/delete",
            json={"repo_id": "org/m", "filename": "model.gguf"},
        )

        assert response.status_code == 404

    @patch(PATCH_DB)
    @patch(PATCH_REG)
    def test_delete_missing_filename_returns_400(
        self, mock_get_reg: MagicMock, mock_get_db: MagicMock, client: TestClient
    ) -> None:
        response = client.post(
            "/api/v1/admin/models/delete",
            json={"repo_id": "org/m"},
        )

        assert response.status_code == 400


# ── POST /api/v1/admin/models/delete-embedding ────────────────────────────


class TestModelsDeleteEmbedding:
    @patch(PATCH_DB)
    @patch(PATCH_REG)
    def test_delete_embedding_removes_model(
        self, mock_get_reg: MagicMock, mock_get_db: MagicMock, client: TestClient
    ) -> None:
        reg = MagicMock()
        reg.get_embedding.return_value = {
            "local_path": "/data/models/embeddings/org/emb",
            "file_size": 0,
            "status": "ready",
        }
        mock_get_reg.return_value = reg

        with patch("src.config.settings.EMBEDDINGS_DIR", new="/data/models/embeddings"):
            response = client.post(
                "/api/v1/admin/models/delete-embedding",
                json={"repo_id": "org/emb"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        reg.remove_embedding.assert_called_once_with("org/emb", mock_get_db.return_value)

    @patch(PATCH_DB)
    @patch(PATCH_REG)
    def test_delete_embedding_not_found_returns_404(
        self, mock_get_reg: MagicMock, mock_get_db: MagicMock, client: TestClient
    ) -> None:
        reg = MagicMock()
        reg.get_embedding.return_value = None
        mock_get_reg.return_value = reg

        response = client.post(
            "/api/v1/admin/models/delete-embedding",
            json={"repo_id": "org/emb"},
        )

        assert response.status_code == 404

    @patch(PATCH_DB)
    @patch(PATCH_REG)
    def test_delete_embedding_missing_repo_id_returns_400(
        self, mock_get_reg: MagicMock, mock_get_db: MagicMock, client: TestClient
    ) -> None:
        response = client.post(
            "/api/v1/admin/models/delete-embedding",
            json={},
        )

        assert response.status_code == 400
