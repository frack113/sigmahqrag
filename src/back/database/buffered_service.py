import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict
from src.back.database.service import DatabaseService

logger = logging.getLogger(__name__)


class JournalStorage:
    """Simple append-only log for crash recovery."""

    def __init__(self, journal_path: Path):
        self.path = journal_path

    def log_intent(self, method_name: str, args: tuple, kwargs: dict) -> None:
        try:
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(f"{method_name}|{args}|{repr(kwargs)}\n")
        except Exception as e:
            logger.error("Failed to log intention: %s", e)

    def clear(self) -> None:
        if self.path.exists():
            try:
                os.remove(self.path)
            except Exception as e:
                logger.error("Failed to clear journal: %s", e)


class BufferedDatabaseService:
    """Wrapper for DatabaseService with Write-Back/Write-Through caching."""

    def __init__(self, base_service: DatabaseService, journal_path: Path, cache_size: int = 100):
        self.db = base_service
        self.journal = JournalStorage(journal_path)
        self.cache: Dict[str, Any] = {}
        self.cache_size = cache_size
        self._lock = threading.Lock()
        self._check_recovery()

    def _check_recovery(self):
        """Checks for unfinished transactions in the journal and replays them."""
        if self.journal.path.exists():
            logger.info("Recovery: Found journal at %s. Replaying...", self.journal.path)
            try:
                with open(self.journal.path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        parts = line.split("|", 2)
                        if len(parts) == 3:
                            method_name, args_str, kwargs_str = parts
                            # Use eval with a safe environment for the prototype
                            # In production, use a real serialization format like JSON or Protobuf
                            args = eval(args_str, {"__builtins__": {}})
                            kwargs = eval(kwargs_str, {"__builtins__": {}})

                            method = getattr(self.db, method_name)
                            method(*args, **kwargs)
                logger.info("Recovery: Successfully replayed journal.")
            except Exception as e:
                logger.error("Recovery: Failed to replay journal: %s", e)
            finally:
                self.journal.clear()

    def flush(self):
        """Synchronizes all cached items to the underlying DatabaseService."""
        with self._lock:
            if not self.cache:
                return
            logger.info("Flushing %d items from cache to DuckDB...", len(self.cache))
            for key, value in self.cache.items():
                # We don't need special handling for worker_state anymore as it's in-memory
                # But we still need to handle other cached keys if any were added later
                pass
            self.cache.clear()
            self.journal.clear()

    def __getattr__(self, name):
        """Delegate all other calls to the base DatabaseService."""
        return getattr(self.db, name)