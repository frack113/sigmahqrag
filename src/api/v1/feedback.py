"""Feedback API v1."""

import logging

from fastapi import APIRouter, Depends, Header, Response
from fastapi.responses import JSONResponse

from src.back.feedback.models import FeedbackIn, FeedbackResponse
from src.back.feedback.service import FeedbackService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/feedback", tags=["v1-feedback"])


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


@router.get("")
async def get_feedback() -> JSONResponse:
    """Get all feedback."""
    service = FeedbackService()
    feedbacks = await service.get_all_feedback()
    return JSONResponse(
        content={
            "feedbacks": [
                {
                    "query": f"query:{f.query_hash}",
                    "helpful": f.helpful,
                }
                for f in feedbacks
            ]
        }
    )


@router.get("/stats")
async def get_feedback_stats() -> JSONResponse:
    """Get feedback statistics."""
    service = FeedbackService()
    stats = await service.get_feedback_stats()
    return JSONResponse(content=stats.model_dump())
