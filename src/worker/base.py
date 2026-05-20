from abc import ABC, abstractmethod
from src.back.database.service import DatabaseService


class BaseWorker(ABC):
    """Abstract base class for all specialized workers."""

    def __init__(self, db: DatabaseService):
        self.db = db

    @abstractmethod
    async def process(self, task: dict) -> None:
        """Execute the logic for a specific task."""
        pass
