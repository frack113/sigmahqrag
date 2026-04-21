"""Retriever."""

from typing import Any


class Retriever:
    """Document retriever."""

    def __init__(self) -> None:
        """Initialize the retriever."""
        pass

    def retrieve(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve documents."""
        return []
