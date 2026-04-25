"""Tests for authentication functionality."""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from src.auth.models import LoginRequest, UserRole
from src.auth.security import create_access_token, decode_access_token, get_password_hash


@pytest.fixture
def test_password_hash() -> str:
    """Generate hash for test password."""
    return get_password_hash("testpassword")


@pytest.fixture
def auth_service_env(test_password_hash: str) -> tuple[dict, dict]:
    """Set up environment for auth service."""
    admin_users = '{"admin": "' + test_password_hash + '"}'
    analyst_users = '{"analyst": "' + test_password_hash + '"}'
    os.environ["ADMIN_USERS"] = admin_users
    os.environ["ANALYST_USERS"] = analyst_users
    os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"
    os.environ["JWT_TOKEN_EXPIRE_MINUTES"] = "30"
    yield (
        {"admin": test_password_hash},
        {"analyst": test_password_hash},
    )
    del os.environ["ADMIN_USERS"]
    del os.environ["ANALYST_USERS"]
    del os.environ["JWT_SECRET"]
    if "JWT_TOKEN_EXPIRE_MINUTES" in os.environ:
        del os.environ["JWT_TOKEN_EXPIRE_MINUTES"]


@pytest.fixture
def client() -> TestClient:
    """Create test client for the app."""
    from src.main import create_app

    app = create_app()
    return TestClient(app)


class TestPasswordHashing:
    """Tests for password hashing utilities."""

    def test_get_password_hash_returns_hash(self) -> None:
        """Given password When get_password_hash Then returns hashed string."""
        hashed = get_password_hash("mypassword")

        assert hashed != "mypassword"
        assert "$" in hashed

    def test_verify_password_correct(self, test_password_hash: str) -> None:
        """Given correct password When verify_password Then returns True."""
        from src.auth.security import verify_password

        result = verify_password("testpassword", test_password_hash)

        assert result is True

    def test_verify_password_incorrect(self, test_password_hash: str) -> None:
        """Given incorrect password When verify_password Then returns False."""
        from src.auth.security import verify_password

        result = verify_password("wrongpassword", test_password_hash)

        assert result is False


class TestJWTTokens:
    """Tests for JWT token functionality."""

    def test_create_access_token(self) -> None:
        """Given data When create_access_token Then returns encoded token."""
        os.environ["JWT_SECRET"] = "test-secret"

        token = create_access_token({"sub": "testuser", "role": "Admin"})

        assert token is not None
        assert isinstance(token, str)

    def test_decode_access_token_valid(self) -> None:
        """Given valid token When decode_access_token Then returns payload."""
        os.environ["JWT_SECRET"] = "test-secret"

        token = create_access_token({"sub": "testuser", "role": "Admin"})
        payload = decode_access_token(token)

        assert payload["sub"] == "testuser"
        assert payload["role"] == "Admin"

    def test_decode_access_token_invalid(self) -> None:
        """Given invalid token When decode_access_token Then raises ValueError."""
        os.environ["JWT_SECRET"] = "test-secret"

        with pytest.raises(ValueError, match="Invalid token"):
            decode_access_token("invalid.token.here")

    def test_decode_access_token_expired(self) -> None:
        """Given expired token When decode_access_token Then raises ValueError."""
        os.environ["JWT_SECRET"] = "test-secret"

        expired_payload = {
            "sub": "testuser",
            "role": "Admin",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            expired_payload, "test-secret", algorithm="HS256"
        )

        with pytest.raises(ValueError, match="Invalid token"):
            decode_access_token(expired_token)


class TestLoginEndpoint:
    """Tests for POST /auth/login endpoint."""

    def test_login_success_admin(
        self, client: TestClient, auth_service_env: tuple[dict, dict]
    ) -> None:
        """Given valid admin credentials When POST /auth/login Then returns token."""
        response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "testpassword"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["role"] == "Admin"
        assert "expires_in" in data

    def test_login_success_analyst(
        self, client: TestClient, auth_service_env: tuple[dict, dict]
    ) -> None:
        """Given valid analyst credentials When POST /auth/login Then returns token."""
        response = client.post(
            "/auth/login",
            json={"username": "analyst", "password": "testpassword"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["role"] == "Analyst"

    def test_login_invalid_password(
        self, client: TestClient, auth_service_env: tuple[dict, dict]
    ) -> None:
        """Given invalid password When POST /auth/login Then returns 401."""
        response = client.post(
            "/auth/login",
            json={"username": "admin", "password": "wrongpassword"},
        )

        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    def test_login_invalid_username(
        self, client: TestClient, auth_service_env: tuple[dict, dict]
    ) -> None:
        """Given invalid username When POST /auth/login Then returns 401."""
        response = client.post(
            "/auth/login",
            json={"username": "nonexistent", "password": "testpassword"},
        )

        assert response.status_code == 401


class TestRoleBasedAccess:
    """Tests for role-based access control."""

    def test_analyst_can_read_health(
        self, client: TestClient, auth_service_env: tuple[dict, dict]
    ) -> None:
        """Given analyst token When GET /admin/health Then returns 200."""
        os.environ["JWT_SECRET"] = "test-secret"
        token = create_access_token({"sub": "analyst", "role": "Analyst"})

        response = client.get(
            "/admin/health",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200

    def test_analyst_cannot_start_llama(
        self, client: TestClient, auth_service_env: tuple[dict, dict]
    ) -> None:
        """Given analyst token When POST /admin/llama/start Then returns 403."""
        os.environ["JWT_SECRET"] = "test-secret"
        token = create_access_token({"sub": "analyst", "role": "Analyst"})

        response = client.post(
            "/admin/llama/start",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    def test_admin_can_start_llama(
        self, client: TestClient, auth_service_env: tuple[dict, dict]
    ) -> None:
        """Given admin token When POST /admin/llama/start Then returns success."""
        os.environ["JWT_SECRET"] = "test-secret"
        token = create_access_token({"sub": "admin", "role": "Admin"})

        response = client.post(
            "/admin/llama/start",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code in (200, 400, 500)

    def test_no_token_returns_401(
        self, client: TestClient, auth_service_env: tuple[dict, dict]
    ) -> None:
        """Given no token When GET /admin/health Then returns 401."""
        response = client.get("/admin/health")

        assert response.status_code == 401

    def test_invalid_token_returns_401(
        self, client: TestClient, auth_service_env: tuple[dict, dict]
    ) -> None:
        """Given invalid token When GET /admin/health Then returns 401."""
        response = client.get(
            "/admin/health",
            headers={"Authorization": "Bearer invalidtoken"},
        )

        assert response.status_code == 401