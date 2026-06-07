from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.infrastructure.database.service import DatabaseService
    from src.workers.processor import TaskDispatcher


class BaseWorker(ABC):
    """Abstract base class for all specialized workers."""

    def __init__(self, db: "DatabaseService", dispatcher: "TaskDispatcher | None" = None):
        self.db = db
        self.dispatcher: "TaskDispatcher | None" = dispatcher

    @abstractmethod
    def process(self, task: dict) -> None:
        """Execute the logic for a specific task."""
        pass
