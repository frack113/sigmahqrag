"""FastAPI dependencies."""

from functools import lru_cache

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.auth.models import CurrentUser, UserRole
from src.auth.security import decode_access_token

security = HTTPBearer(auto_error=False)


@lru_cache
def get_settings() -> dict:
    """Get application settings."""
    return {
        "app_name": "SigmaHQ RAG",
        "version": "0.1.0",
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> CurrentUser:
    """Get current authenticated user from JWT token.

    Args:
        credentials: Bearer token from Authorization header

    Returns:
        CurrentUser with username and role

    Raises:
        HTTPException: If token invalid or missing
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(credentials.credentials)
        username = payload.get("sub")
        role = payload.get("role")

        if not username or not role:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token claims",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return CurrentUser(username=username, role=UserRole(role))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def require_role(*allowed_roles: UserRole):
    """Create dependency that checks user has required role.

    Args:
        allowed_roles: Roles that are allowed access

    Returns:
        Dependency function that returns CurrentUser if role allowed

    Example:
        @router.get("/admin/users")
        def get_users(current_user: CurrentUser = Depends(require_role(UserRole.ADMIN))) -> list:
            ...
    """

    async def role_checker(
        current_user: CurrentUser = Depends(get_current_user),
    ) -> CurrentUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not allowed. Required: {[r.value for r in allowed_roles]}",
            )
        return current_user

    return role_checker
