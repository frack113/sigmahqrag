"""Tests for feedback functionality."""

import os
import tempfile
import uuid

import pytest

from src.back.feedback.models import (
    FeedbackIn,
    FeedbackResponse,
    FeedbackStats,
    hash_query,
)
from src.back.feedback.repository import FeedbackRepository
from src.back.feedback.service import FeedbackService


@pytest.fixture
def temp_db_path() -> str:
    """Create a temporary database path."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
        path = f.name
    yield path
    if os.path.exists(path):
        os.remove(path)


@pytest.fixture
def feedback_repo(temp_db_path: str) -> FeedbackRepository:
    """Create a feedback repository with temp DB."""
    return FeedbackRepository(db_path=temp_db_path)


@pytest.fixture
def feedback_service(feedback_repo: FeedbackRepository) -> FeedbackService:
    """Create feedback service with test repo."""
    return FeedbackService(repository=feedback_repo)


class TestHashQuery:
    """Tests for query hashing."""

    def test_hash_query_returns_string(self) -> None:
        """Given query When hash_query Then returns hashed string."""
        result = hash_query("test query")

        assert isinstance(result, str)
        assert len(result) > 0

    def test_hash_query_same_input_same_output(self) -> None:
        """Given same query When hash_query Then returns same hash."""
        query = "test query"
        result1 = hash_query(query)
        result2 = hash_query(query)

        assert result1 == result2

    def test_hash_query_different_input_different_output(self) -> None:
        """Given different queries When hash_query Then returns different hashes."""
        result1 = hash_query("query one")
        result2 = hash_query("query two")

        assert result1 != result2

    def test_hash_query_anonymity(self) -> None:
        """Given query When hash_query Then does not reveal original."""
        query = "sensitive_data_123"
        result = hash_query(query)

        assert "sensitive_data" not in result


class TestFeedbackModels:
    """Tests for feedback Pydantic models."""

    def test_feedback_in_valid(self) -> None:
        """Given valid input When creating FeedbackIn Then succeeds."""
        feedback = FeedbackIn(query="test query", helpful=True)

        assert feedback.query == "test query"
        assert feedback.helpful is True

    def test_feedback_response_structure(self) -> None:
        """Given feedback created When creating response Then has required fields."""
        feedback_id = str(uuid.uuid4())
        response = FeedbackResponse(feedback_id=feedback_id)

        assert response.feedback_id == feedback_id
        assert response.message is not None

    def test_feedback_stats_calculation(self) -> None:
        """Given feedback data When creating stats Then calculates correctly."""
        stats = FeedbackStats(
            total=100,
            helpful_count=75,
            not_helpful_count=25,
            helpful_percentage=75.0,
        )

        assert stats.total == 100
        assert stats.helpful_count == 75
        assert stats.helpful_percentage == 75.0


class TestResolveDbPath:
    def test_absolute_path(self) -> None:
        repo = FeedbackRepository(db_path="C:\\absolute\\path.db")
        assert str(repo._db_path) == "C:\\absolute\\path.db"

    def test_relative_path(self) -> None:
        repo = FeedbackRepository(db_path="relative.db")
        assert "relative.db" in str(repo._db_path)


class TestFeedbackRepository:
    """Tests for feedback repository."""

    @pytest.mark.asyncio
    async def test_initialize_creates_table(self, feedback_repo: FeedbackRepository) -> None:
        """Given new repository When initialize Then creates table."""
        await feedback_repo.initialize()

        import aiosqlite

        async with aiosqlite.connect(feedback_repo._db_path) as db:
            async with db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='feedback'"
            ) as cursor:
                result = await cursor.fetchone()

        assert result is not None

    @pytest.mark.asyncio
    async def test_create_feedback(self, feedback_repo: FeedbackRepository) -> None:
        """Given feedback data When create Then returns feedback object."""
        feedback = await feedback_repo.create(query="test query", helpful=True)

        assert feedback.id is not None
        assert feedback.query_hash is not None
        assert feedback.helpful is True

    @pytest.mark.asyncio
    async def test_get_all_returns_created(self, feedback_repo: FeedbackRepository) -> None:
        """Given created feedback When get_all Then includes it."""
        created = await feedback_repo.create(query="test", helpful=True)
        all_feedback = await feedback_repo.get_all()

        assert len(all_feedback) >= 1
        assert any(f.id == created.id for f in all_feedback)

    @pytest.mark.asyncio
    async def test_get_stats_empty(self, feedback_repo: FeedbackRepository) -> None:
        """Given empty database When get_stats Then returns zeros."""
        await feedback_repo.initialize()
        stats = await feedback_repo.get_stats()

        assert stats.total == 0
        assert stats.helpful_count == 0

    @pytest.mark.asyncio
    async def test_get_stats_with_data(self, feedback_repo: FeedbackRepository) -> None:
        """Given feedback data When get_stats Then calculates correctly."""
        await feedback_repo.create(query="test1", helpful=True)
        await feedback_repo.create(query="test2", helpful=True)
        await feedback_repo.create(query="test3", helpful=False)

        stats = await feedback_repo.get_stats()

        assert stats.total == 3
        assert stats.helpful_count == 2
        assert stats.not_helpful_count == 1

    @pytest.mark.asyncio
    async def test_get_by_date_range_returns_matching(
        self,
        feedback_repo: FeedbackRepository,
    ) -> None:
        """Given feedback When date range matches Then returns entries."""
        from datetime import datetime, timedelta

        now = datetime.now()
        feedback = await feedback_repo.create(query="test", helpful=True)
        all_in_range = await feedback_repo.get_by_date_range(
            now - timedelta(hours=1), now + timedelta(hours=1)
        )
        assert any(f.id == feedback.id for f in all_in_range)

    @pytest.mark.asyncio
    async def test_get_by_date_range_empty_when_outside(
        self,
        feedback_repo: FeedbackRepository,
    ) -> None:
        """Given feedback When date range doesn't match Then returns empty."""
        from datetime import datetime

        await feedback_repo.create(query="test", helpful=True)
        result = await feedback_repo.get_by_date_range(datetime(2020, 1, 1), datetime(2020, 1, 2))
        assert result == []


class TestFeedbackService:
    """Tests for feedback service."""

    @pytest.mark.asyncio
    async def test_submit_feedback(self, feedback_service: FeedbackService) -> None:
        """Given feedback input When submit Then returns response."""
        feedback_in = FeedbackIn(query="test query", helpful=True)
        result = await feedback_service.submit_feedback(feedback_in)

        assert isinstance(result, FeedbackResponse)
        assert result.feedback_id is not None

    @pytest.mark.asyncio
    async def test_get_all_feedback(self, feedback_service: FeedbackService) -> None:
        """When get_all_feedback Then returns list."""
        await feedback_service.submit_feedback(FeedbackIn(query="test", helpful=True))
        result = await feedback_service.get_all_feedback()

        assert isinstance(result, list)
        assert len(result) >= 1

    @pytest.mark.asyncio
    async def test_get_feedback_stats(self, feedback_service: FeedbackService) -> None:
        """When get_feedback_stats Then returns stats."""
        await feedback_service.submit_feedback(FeedbackIn(query="test", helpful=True))
        result = await feedback_service.get_feedback_stats()

        assert isinstance(result, FeedbackStats)


class TestNoAuthRequired:
    """Tests for no authentication requirement (AC #3)."""

    @pytest.mark.asyncio
    async def test_submit_without_session(self, feedback_repo: FeedbackRepository) -> None:
        """Given no session ID When submit Then accepts anyway."""
        feedback = await feedback_repo.create(query="test query", helpful=True, session_id=None)

        assert feedback.session_id is None
        assert feedback.id is not None


class TestErrorHandling:
    """Tests for error handling."""

    @pytest.mark.asyncio
    async def test_get_stats_divide_by_zero(self, feedback_repo: FeedbackRepository) -> None:
        """Given no data When get_stats Then handles gracefully."""
        await feedback_repo.initialize()
        stats = await feedback_repo.get_stats()

        assert stats.total == 0
        assert stats.helpful_percentage == 0.0
