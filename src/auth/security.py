"""Security utilities for password hashing and JWT tokens."""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

SECRET_KEY: str | None = None
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def get_jwt_secret() -> str:
    """Get JWT secret from environment."""
    global SECRET_KEY
    if SECRET_KEY is None:
        import os

        SECRET_KEY = os.environ.get("JWT_SECRET")
        if not SECRET_KEY:
            raise ValueError("JWT_SECRET environment variable not set")
    return SECRET_KEY


def get_token_expire_minutes() -> int:
    """Get token expiration in minutes from environment."""
    global ACCESS_TOKEN_EXPIRE_MINUTES
    import os

    val = os.environ.get("JWT_TOKEN_EXPIRE_MINUTES")
    if val:
        ACCESS_TOKEN_EXPIRE_MINUTES = int(val)
    return ACCESS_TOKEN_EXPIRE_MINUTES


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create JWT access token.

    Args:
        data: Token claims including sub (username) and role
        expires_delta: Optional custom expiration

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=get_token_expire_minutes()
        )

    to_encode.update({"exp": expire, "iat": datetime.now(UTC)})
    encoded_jwt = jwt.encode(to_encode, get_jwt_secret(), algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify JWT access token.

    Args:
        token: JWT token string

    Returns:
        Decoded token claims

    Raises:
        ValueError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token, get_jwt_secret(), algorithms=[ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {e}") from e


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    import bcrypt

    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.

    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password to compare against

    Returns:
        True if password matches, False otherwise
    """
    import bcrypt

    return bcrypt.checkpw(
        plain_password.encode(), hashed_password.encode()
    )
