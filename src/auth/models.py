"""Auth models and schemas."""

from enum import StrEnum

from pydantic import BaseModel


class UserRole(StrEnum):
    """User role enumeration."""

    ANALYST = "Analyst"
    ADMIN = "Admin"


class LoginRequest(BaseModel):
    """Login request schema."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Token response schema."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: UserRole


class CurrentUser(BaseModel):
    """Current authenticated user schema."""

    username: str
    role: UserRole
