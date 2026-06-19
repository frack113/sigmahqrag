from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from src.main import create_app


@pytest.fixture
def app() -> Any:
    return create_app()


@pytest.mark.asyncio
async def test_config_page_route(app: Any):
    """Test that /config returns the config landing page."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/config")
        assert response.status_code in (200, 302)  # 302 if redirected to /setup


@pytest.mark.asyncio
async def test_config_system_redirect(app: Any):
    """Test that /config/system redirects to /config."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.get("/config/system", follow_redirects=False)
        assert response.status_code in (307, 302)
        assert response.headers.get("location") == "/config"
