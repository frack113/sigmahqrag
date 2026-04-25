"""Feedback API routes."""

import logging

from fastapi import APIRouter, Depends, Header, Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.feedback.models import FeedbackIn, FeedbackResponse, FeedbackStats
from src.feedback.service import FeedbackService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])
security = HTTPBearer(auto_error=False)


async def get_current_admin_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """Dependency to verify admin role."""
    if credentials is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Not authenticated")

    import os

    from jose import JWTError, jwt

    try:
        secret = os.getenv("JWT_SECRET", "default-secret")
        payload = jwt.decode(credentials.credentials, secret, algorithms=["HS256"])
        role = payload.get("role")
        if role != "Admin":
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Admin required")
        return payload.get("sub", "admin")
    except JWTError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid token") from e


def get_session_id(x_session_id: str | None = Header(None)) -> str | None:
    """Extract session ID from header."""
    return x_session_id


@router.post("", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    feedback_in: FeedbackIn,
    response: Response,
    session_id: str | None = Depends(get_session_id),
) -> FeedbackResponse:
    """Submit feedback for search results."""
    service = FeedbackService()
    result = await service.submit_feedback(feedback_in, session_id)
    response.headers["X-Feedback-ID"] = result.feedback_id
    return result


@router.get("", response_model=list[FeedbackIn])
async def get_feedback(
    _: str = Depends(get_current_admin_user),
) -> list[FeedbackIn]:
    """Get all feedback (admin only)."""
    service = FeedbackService()
    feedbacks = await service.get_all_feedback()
    return [
        FeedbackIn(
            query=f"query:{f.query_hash}",
            helpful=f.helpful,
        )
        for f in feedbacks
    ]


@router.get("/stats", response_model=FeedbackStats)
async def get_feedback_stats(
    _: str = Depends(get_current_admin_user),
) -> FeedbackStats:
    """Get feedback statistics (admin only)."""
    service = FeedbackService()
    return await service.get_feedback_stats()
