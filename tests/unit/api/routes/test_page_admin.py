from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

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
        # We expect HTML content (not JSON)
        assert response.headers["content-type"].startswith("text/html")
        assert "Sigmahqrag" in response.text


@pytest.mark.asyncio
async def test_admin_health_route(app: Any):
    """Test that /admin/health returns the health check page."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/admin/health")
        assert response.status_code == 200
        # Returns HTML template (admin/health.html)
        assert response.headers["content-type"].startswith("text/html")


@pytest.mark.asyncio
async def test_admin_logs_route(app: Any):
    """Test that /admin/logs redirects to /logs."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/admin/logs", follow_redirects=False)
        assert response.status_code in (307, 302)
        assert response.headers.get("location") == "/logs"
