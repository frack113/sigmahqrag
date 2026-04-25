"""Authentication service."""

import json
import os
from dataclasses import dataclass
from typing import Any

from src.auth.models import LoginRequest, TokenResponse, UserRole
from src.auth.security import create_access_token, get_token_expire_minutes


@dataclass
class User:
    """User data class."""

    username: str
    hashed_password: str
    role: UserRole


class AuthService:
    """Authentication service."""

    def __init__(self, admin_users: dict[str, str], analyst_users: dict[str, str]) -> None:
        """Initialize auth service with user stores.

        Args:
            admin_users: Dict mapping username to bcrypt hashed password
            analyst_users: Dict mapping username to bcrypt hashed password
        """
        self._users: dict[str, User] = {}
        for username, password in admin_users.items():
            self._users[username] = User(username, password, UserRole.ADMIN)
        for username, password in analyst_users.items():
            self._users[username] = User(username, password, UserRole.ANALYST)

    def authenticate(self, request: LoginRequest) -> TokenResponse | None:
        """Authenticate user with credentials.

        Args:
            request: Login request with username and password

        Returns:
            TokenResponse if credentials valid, None otherwise
        """
        user = self._users.get(request.username)
        if not user:
            return None

        from src.auth.security import verify_password

        if not verify_password(request.password, user.hashed_password):
            return None

        token_data = {"sub": user.username, "role": user.role.value}
        access_token = create_access_token(token_data)
        expires_in = get_token_expire_minutes() * 60

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=expires_in,
            role=user.role,
        )

    def get_current_user(self, token: str) -> dict[str, Any] | None:
        """Get current user from JWT token.

        Args:
            token: JWT token string

        Returns:
            User info dict if valid, None otherwise
        """
        try:
            from src.auth.security import decode_access_token

            payload = decode_access_token(token)
            return payload
        except ValueError:
            return None


def create_auth_service() -> AuthService:
    """Create auth service from environment configuration.

    Returns:
        AuthService instance

    Raises:
        ValueError: If required config missing
    """
    admin_json = os.environ.get("ADMIN_USERS")
    analyst_json = os.environ.get("ANALYST_USERS")

    if not admin_json:
        raise ValueError("ADMIN_USERS environment variable not set")
    if not analyst_json:
        raise ValueError("ANALYST_USERS environment variable not set")

    admin_users: dict[str, str] = json.loads(admin_json)
    analyst_users: dict[str, str] = json.loads(analyst_json)

    return AuthService(admin_users, analyst_users)
