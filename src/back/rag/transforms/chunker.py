"""Document chunker."""

from typing import Any


class Chunker:
    """Document chunker."""

    def __init__(self, max_chunk_size: int = 512) -> None:
        """Initialize the chunker."""
        self.max_chunk_size = max_chunk_size

    def chunk(self, document: dict[str, Any]) -> list[dict[str, Any]]:
        """Chunk a document."""
        return []
