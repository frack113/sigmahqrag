"""Tests for admin API routes."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from src.api.routes.admin_service import _get_status_display
from src.shared.health import ServiceHealth, ServiceStatus


@pytest.fixture
def mock_llama_health() -> ServiceHealth:
    """Mock llama.cpp running health."""
    return ServiceHealth(
        name="llama.cpp",
        status=ServiceStatus.RUNNING,
        port=8080,
        url="http://localhost:8080/v1/models",
    )


@pytest.fixture
def mock_qdrant_health() -> ServiceHealth:
    """Mock Qdrant running health."""
    return ServiceHealth(
        name="qdrant",
        status=ServiceStatus.RUNNING,
        port=6333,
        url="http://localhost:6333/health",
    )


@pytest.fixture
def mock_llama_stopped() -> ServiceHealth:
    """Mock llama.cpp stopped health."""
    return ServiceHealth(
        name="llama.cpp",
        status=ServiceStatus.STOPPED,
        port=8080,
        url="http://localhost:8080/v1/models",
        message="Connection refused",
    )


@pytest.fixture
def client() -> TestClient:
    """Create test client for the app."""
    from src.main import create_app

    app = create_app()
    return TestClient(app)


class TestGetStatusDisplay:
    """Tests for _get_status_display function."""

    def test_running_status_returns_green(
        self, mock_llama_health: ServiceHealth, tmp_path: Path
    ) -> None:
        """Given running service When _get_status_display Then returns green color."""
        binary_path = tmp_path / "bin" / "llama-server"
        binary_path.parent.mkdir()
        binary_path.touch()
        result = _get_status_display(mock_llama_health, binary_path)

        assert result["color"] == "green"
        assert result["status"] == "running"

    def test_stopped_status_returns_red(
        self, mock_llama_stopped: ServiceHealth, tmp_path: Path
    ) -> None:
        """Given stopped service When _get_status_display Then returns red color."""
        binary_path = tmp_path / "bin" / "llama-server"
        binary_path.parent.mkdir()
        binary_path.touch()
        result = _get_status_display(mock_llama_stopped, binary_path)

        assert result["color"] == "red"
        assert result["status"] == "stopped"

    def test_not_installed_returns_yellow(
        self, mock_llama_stopped: ServiceHealth, tmp_path: Path
    ) -> None:
        """Given missing binary When _get_status_display Then returns yellow."""
        binary_path = tmp_path / "bin" / "llama-server"
        binary_path.parent.mkdir(parents=True)
        result = _get_status_display(mock_llama_stopped, binary_path)

        assert result["color"] == "yellow"
        assert result["status"] == "not installed"

    def test_not_installed_when_binary_missing(
        self, mock_llama_health: ServiceHealth, tmp_path: Path
    ) -> None:
        """Given binary not found When _get_status_display Then returns not installed."""
        non_existent_path = tmp_path / "nonexistent"
        result = _get_status_display(mock_llama_health, non_existent_path)

        assert result["status"] == "not installed"
        assert result["color"] == "yellow"
        assert "Binary not found" in result["message"]

    def test_message_included_when_present(
        self, mock_llama_stopped: ServiceHealth, tmp_path: Path
    ) -> None:
        """Given health with message When _get_status_display Then message included."""
        binary_path = tmp_path / "bin" / "llama-server"
        binary_path.parent.mkdir()
        binary_path.touch()
        result = _get_status_display(mock_llama_stopped, binary_path)

        assert result["message"] == "Connection refused"


class TestAdminHealthEndpoint:
    """Tests for GET /admin/health endpoint."""

    def test_health_endpoint_returns_services(
        self,
        client: TestClient,
        mock_llama_health: ServiceHealth,
        mock_qdrant_health: ServiceHealth,
    ) -> None:
        """Given services are running When GET /admin/health Then returns service statuses."""
        with patch("src.shared.health.create_health_checker") as mock_checker:
            mock_instance = AsyncMock()
            mock_instance.check_all.return_value = {
                "llama": mock_llama_health,
                "qdrant": mock_qdrant_health,
            }
            mock_checker.return_value = mock_instance

            response = client.get("/admin/health")

            assert response.status_code == 200
            data = response.json()
            assert "services" in data
            assert len(data["services"]) == 2
