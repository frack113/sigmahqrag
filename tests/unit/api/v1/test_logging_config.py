"""Tests for logging configuration API endpoints."""

from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from src.api.v1.system.config import LoggingConfigUpdateRequest, LOG_LEVELS
from src.config.settings import Config
from src.infrastructure.database import DatabaseService


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
def patched_config(db: DatabaseService, monkeypatch: pytest.MonkeyPatch) -> Config:
    cfg = Config()
    monkeypatch.setattr("src.config.settings._config", cfg)
    return cfg


@pytest.fixture
def client(db: DatabaseService, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    from src.main import create_app

    app = create_app()
    app.state.db = db
    DatabaseService._instance = db
    return TestClient(app)


class TestLoggingConfigUpdateRequest:
    """Test the Pydantic validation model."""

    def test_valid_level_accepted(self) -> None:
        for level in LOG_LEVELS:
            req = LoggingConfigUpdateRequest(level=level)
            assert req.level == level

    def test_none_level_accepted(self) -> None:
        req = LoggingConfigUpdateRequest(level=None)
        assert req.level is None

    def test_invalid_level_rejected(self) -> None:
        with pytest.raises(Exception):
            LoggingConfigUpdateRequest(level="INVALID")

    def test_empty_string_level_rejected(self) -> None:
        with pytest.raises(Exception):
            LoggingConfigUpdateRequest(level="")

    def test_numeric_level_rejected(self) -> None:
        with pytest.raises(Exception):
            LoggingConfigUpdateRequest(level=42)

    def test_partial_update(self) -> None:
        req = LoggingConfigUpdateRequest(level="WARNING")
        assert req.level == "WARNING"
        assert req.log_max_size is None
        assert req.log_max_file is None
        assert req.clean_at_startup is None

    def test_all_fields_set(self) -> None:
        req = LoggingConfigUpdateRequest(
            level="ERROR",
            log_max_size="50M",
            log_max_file=10,
            clean_at_startup=True,
        )
        assert req.level == "ERROR"
        assert req.log_max_size == "50M"
        assert req.log_max_file == 10
        assert req.clean_at_startup is True


class TestGetLoggingConfig:
    """Test GET /api/v1/config/logging."""

    def test_returns_logging_config(self, client: TestClient) -> None:
        resp = client.get("/api/v1/config/logging")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert "level" in data["data"]
        assert "log_max_size" in data["data"]
        assert "log_max_file" in data["data"]
        assert "clean_at_startup" in data["data"]

    def test_default_values(self, client: TestClient, patched_config: Config) -> None:
        resp = client.get("/api/v1/config/logging")
        data = resp.json()
        assert data["data"]["level"] == patched_config.logging_level
        assert data["data"]["log_max_size"] == patched_config.logging_log_max_size
        assert data["data"]["log_max_file"] == patched_config.logging_log_max_file
        assert data["data"]["clean_at_startup"] == patched_config.logging_clean_at_startup


class TestUpdateLoggingConfig:
    """Test POST /api/v1/config/logging."""

    def test_update_level(
        self, client: TestClient, patched_config: Config, db: DatabaseService
    ) -> None:
        resp = client.post("/api/v1/config/logging", json={"level": "WARNING"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["data"]["level"] == "WARNING"
        assert patched_config.logging_level == "WARNING"
        row = db.get_config("logging.level")
        assert row == "WARNING"

    def test_update_log_max_size(
        self, client: TestClient, patched_config: Config, db: DatabaseService
    ) -> None:
        resp = client.post("/api/v1/config/logging", json={"log_max_size": "50M"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["log_max_size"] == "50M"
        assert patched_config.logging_log_max_size == "50M"
        row = db.get_config("logging.log_max_size")
        assert row == "50M"

    def test_update_log_max_file(
        self, client: TestClient, patched_config: Config, db: DatabaseService
    ) -> None:
        resp = client.post("/api/v1/config/logging", json={"log_max_file": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["log_max_file"] == 10
        assert patched_config.logging_log_max_file == 10
        row = db.get_config("logging.log_max_file")
        assert row == 10

    def test_update_clean_at_startup(
        self, client: TestClient, patched_config: Config, db: DatabaseService
    ) -> None:
        resp = client.post("/api/v1/config/logging", json={"clean_at_startup": True})
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["clean_at_startup"] is True
        assert patched_config.logging_clean_at_startup is True
        row = db.get_config("logging.clean_at_startup")
        assert row is True

    def test_invalid_level_rejected(self, client: TestClient) -> None:
        resp = client.post("/api/v1/config/logging", json={"level": "BLABLA"})
        assert resp.status_code == 422

    def test_partial_update(
        self, client: TestClient, patched_config: Config, db: DatabaseService
    ) -> None:
        original_size = patched_config.logging_log_max_size
        original_files = patched_config.logging_log_max_file

        resp = client.post("/api/v1/config/logging", json={"level": "CRITICAL"})
        assert resp.status_code == 200

        assert patched_config.logging_level == "CRITICAL"
        assert patched_config.logging_log_max_size == original_size
        assert patched_config.logging_log_max_file == original_files

    def test_update_all_fields(
        self, client: TestClient, patched_config: Config, db: DatabaseService
    ) -> None:
        resp = client.post(
            "/api/v1/config/logging",
            json={
                "level": "DEBUG",
                "log_max_size": "100M",
                "log_max_file": 20,
                "clean_at_startup": True,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["data"]["level"] == "DEBUG"
        assert data["data"]["log_max_size"] == "100M"
        assert data["data"]["log_max_file"] == 20
        assert data["data"]["clean_at_startup"] is True

    def test_persisted_across_requests(
        self, client: TestClient, patched_config: Config, db: DatabaseService
    ) -> None:
        resp1 = client.post("/api/v1/config/logging", json={"level": "ERROR"})
        assert resp1.status_code == 200

        resp2 = client.get("/api/v1/config/logging")
        data = resp2.json()
        assert data["data"]["level"] == "ERROR"
