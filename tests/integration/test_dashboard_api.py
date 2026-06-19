from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.database import DatabaseService
from src.main import create_app


@pytest.fixture
def db() -> DatabaseService:
    tmp = tempfile.NamedTemporaryFile(suffix=".duckdb", delete=False)
    tmp.close()
    os.unlink(tmp.name)
    d = DatabaseService(tmp.name)
    d.initialize()
    yield d
    d.close()
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


@pytest.fixture
def client(db: DatabaseService) -> TestClient:
    app = create_app()
    app.state.db = db
    DatabaseService._instance = db
    return TestClient(app)


class TestDuckdbAPI:
    def test_list_tables(self, client: TestClient):
        resp = client.get("/api/v1/dashboard/tables")
        assert resp.status_code == 200
        data = resp.json()
        assert "tables" in data
        assert "config" in data["tables"]

    def test_get_table_data(self, client: TestClient):
        resp = client.get("/api/v1/dashboard/tables/config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["table"] == "config"
        assert "rows" in data
        assert "total" in data

    def test_invalid_table_returns_400(self, client: TestClient):
        resp = client.get("/api/v1/dashboard/tables/nonexistent")
        assert resp.status_code == 400

    def test_pagination(self, client: TestClient):
        resp = client.get("/api/v1/dashboard/tables/config?limit=5&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert len(data["rows"]) <= 5

    def test_total_in_response(self, client: TestClient):
        resp = client.get("/api/v1/dashboard/tables/git_selected_dirs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 0

    def test_get_table_data_response_model(self, client: TestClient):
        resp = client.get("/api/v1/dashboard/tables/config")
        data = resp.json()
        assert set(data.keys()) == {"table", "rows", "total", "limit", "offset"}
