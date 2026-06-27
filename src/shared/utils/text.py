"""Text processing utilities for the RAG pipeline."""

MAX_EMBED_CHARS = 3000


def truncate_for_embedding(text: str, max_chars: int = MAX_EMBED_CHARS) -> str:
    """Truncate text to *max_chars* for embedding model context limits.

    Args:
        text: Input text to truncate.
        max_chars: Maximum character length before truncation.

    Returns:
        Truncated text with a truncation marker appended when needed.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[TRUNCATED_FOR_EMBEDDING]"
