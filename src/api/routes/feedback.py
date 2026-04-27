"""Feedback API routes."""

import logging

from fastapi import APIRouter, Depends, Header, Response, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from src.api.dependencies import security, get_current_user, require_role
from src.auth.models import UserRole
from src.feedback.models import FeedbackIn, FeedbackResponse, FeedbackStats
from src.feedback.service import FeedbackService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/feedback", tags=["feedback"])


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
    _: str = Depends(require_role(UserRole.ADMIN)),
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
    _: str = Depends(require_role(UserRole.ADMIN)),
) -> FeedbackStats:
    """Get feedback statistics (admin only)."""
    service = FeedbackService()
    return await service.get_feedback_stats()