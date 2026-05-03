"""Vector store client."""

from typing import Any


class VectorStoreClient:
    """Client for vector store."""

    def __init__(self, path: str = "./qdrant/storage") -> None:
        """Initialize the client."""
        self.path = path

    async def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        """Search vectors."""
        return []

    async def add(
        self, vectors: list[list[float]], documents: list[dict[str, Any]]
    ) -> None:
        """Add vectors."""
        pass
