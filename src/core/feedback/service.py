"""Feedback service for business logic."""

import logging

from src.core.feedback.models import Feedback, FeedbackIn, FeedbackResponse, FeedbackStats
from src.core.feedback.repository import FeedbackRepository

logger = logging.getLogger(__name__)


class FeedbackService:
    """Service for feedback business logic."""

    def __init__(self, repository: FeedbackRepository | None = None):
        self.repository = repository or FeedbackRepository()

    async def submit_feedback(
        self, feedback_in: FeedbackIn, session_id: str | None = None
    ) -> FeedbackResponse:
        """Submit user feedback."""
        feedback = await self.repository.create(
            query=feedback_in.query,
            helpful=feedback_in.helpful,
            session_id=session_id,
        )

        logger.info(f"Feedback submitted: {feedback.id}")
        return FeedbackResponse(feedback_id=feedback.id)

    async def get_all_feedback(self) -> list[Feedback]:
        """Get all feedback entries."""
        return await self.repository.get_all()

    async def get_feedback_stats(self) -> FeedbackStats:
        """Get feedback statistics."""
        return await self.repository.get_stats()
