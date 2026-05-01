import pytest
from typing import Any
from httpx import AsyncClient, ASGITransport
from src.main import create_app

@pytest.fixture
def app() -> Any:
    return create_app()

@pytest.mark.asyncio
async def test_admin_dashboard_route(app: Any):
    """Test that /admin returns the dashboard landing page."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/admin")
        assert response.status_code == 200
        # We expect some admin specific content in the HTML
        assert "Admin Dashboard" in response.text

@pytest.mark.asyncio
async def test_admin_health_route(app: Any):
    """Test that /admin/health returns the health view."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/admin/health")
        assert response.status_code == 200
        assert "Health" in response.text

@pytest.mark.asyncio
async def test_admin_hardware_route(app: Any):
    """Test that /admin/hardware returns the hardware view."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/admin/hardware")
        assert response.status_code == 200
        assert "Hardware" in response.text

@pytest.mark.asyncio
async def test_admin_logs_route(app: Any):
    """Test that /admin/logs returns the logs view."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/admin/logs")
        assert response.status_code == 200
        assert "Logs" in response.text
