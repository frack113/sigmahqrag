"""Feedback repository for database operations."""

import logging
import os
import uuid
from datetime import datetime
from pathlib import Path

import aiosqlite

from src.back.feedback.models import Feedback, FeedbackStats, hash_query

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("FEEDBACK_DB_PATH", "feedback.db")


class FeedbackRepository:
    """Repository for feedback data operations."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or DB_PATH
        self._db_path = self._resolve_db_path()
        self._initialized = False

    def _resolve_db_path(self) -> Path:
        """Resolve database path relative to project root."""
        if Path(self.db_path).is_absolute():
            return Path(self.db_path)
        import src

        root = Path(src.__file__).parent.parent
        return root / self.db_path

    async def initialize(self) -> None:
        """Initialize the database schema."""
        if self._initialized:
            return

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    query_hash TEXT NOT NULL,
                    helpful INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    session_id TEXT
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_timestamp
                ON feedback(timestamp)
            """)
            await db.commit()

        self._initialized = True
        logger.info(f"Feedback database initialized at {self._db_path}")

    async def create(
        self, query: str, helpful: bool, session_id: str | None = None
    ) -> Feedback:
        """Create a new feedback entry."""
        await self.initialize()

        feedback = Feedback(
            id=str(uuid.uuid4()),
            query_hash=hash_query(query),
            helpful=helpful,
            timestamp=datetime.now(),
            session_id=session_id,
        )

        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                """
                INSERT INTO feedback (id, query_hash, helpful, timestamp, session_id)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    feedback.id,
                    feedback.query_hash,
                    1 if feedback.helpful else 0,
                    feedback.timestamp.isoformat(),
                    feedback.session_id,
                ),
            )
            await db.commit()

        logger.info(f"Feedback created: {feedback.id}")
        return feedback

    async def get_all(self) -> list[Feedback]:
        """Get all feedback entries."""
        await self.initialize()

        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM feedback ORDER BY timestamp DESC"
            ) as cursor:
                rows = await cursor.fetchall()

        feedbacks = []
        for row in rows:
            feedbacks.append(
                Feedback(
                    id=row["id"],
                    query_hash=row["query_hash"],
                    helpful=bool(row["helpful"]),
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    session_id=row["session_id"],
                )
            )
        return feedbacks

    async def get_stats(self) -> FeedbackStats:
        """Get feedback statistics."""
        await self.initialize()

        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT COUNT(*) as total FROM feedback") as cursor:
                total = (await cursor.fetchone())[0]

            async with db.execute(
                "SELECT COUNT(*) as count FROM feedback WHERE helpful = 1"
            ) as cursor:
                helpful_count = (await cursor.fetchone())[0]

        not_helpful_count = total - helpful_count
        helpful_percentage = (helpful_count / total * 100) if total > 0 else 0.0

        return FeedbackStats(
            total=total,
            helpful_count=helpful_count,
            not_helpful_count=not_helpful_count,
            helpful_percentage=helpful_percentage,
        )

    async def get_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> list[Feedback]:
        """Get feedback within a date range."""
        await self.initialize()

        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                """
                SELECT * FROM feedback
                WHERE timestamp BETWEEN ? AND ?
                ORDER BY timestamp DESC
            """,
                (start_date.isoformat(), end_date.isoformat()),
            ) as cursor:
                rows = await cursor.fetchall()

        feedbacks = []
        for row in rows:
            feedbacks.append(
                Feedback(
                    id=row["id"],
                    query_hash=row["query_hash"],
                    helpful=bool(row["helpful"]),
                    timestamp=datetime.fromisoformat(row["timestamp"]),
                    session_id=row["session_id"],
                )
            )
        return feedbacks
