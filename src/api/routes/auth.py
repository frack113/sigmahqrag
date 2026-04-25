"""Auth API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from src.auth.models import LoginRequest, TokenResponse
from src.auth.service import AuthService, create_auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

security = HTTPBearer(auto_error=False)


async def get_auth_service() -> AuthService:
    """Get auth service dependency."""
    return create_auth_service()


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    auth_service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Login endpoint to authenticate user and return JWT token.

    Args:
        request: Login credentials
        auth_service: Auth service dependency

    Returns:
        TokenResponse with JWT token

    Raises:
        HTTPException: If credentials invalid
    """
    token_response = auth_service.authenticate(request)

    if not token_response:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return token_response
