"""Chat mode enum."""

from enum import StrEnum


class ChatMode(StrEnum):
    """Chat operation modes."""

    SEARCH = "search"
    EXPLAIN = "explain"
    COVERAGE = "coverage"

    @classmethod
    def values(cls) -> list[str]:
        """Get all mode values."""
        return [m.value for m in cls]
