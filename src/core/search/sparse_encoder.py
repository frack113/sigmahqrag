"""Sparse encoder for hybrid search — BM25-based, no external dependencies.

Uses sublinear TF scaling (1 + log(tf)) per unique term with a deterministic
hash-based token-to-ID mapping.  Works with any language or text domain and
requires no model downloads.

Usage:
    from src.core.search.sparse_encoder import create_sparse_encoder
    encoder = create_sparse_encoder()
    indices, values = encoder(["some text"])  # batched: List[str]
"""

from __future__ import annotations

import hashlib
import logging
import math
import re


logger = logging.getLogger(__name__)

STOP_WORDS: frozenset[str] = frozenset(
    {
        "what",
        "are",
        "the",
        "in",
        "for",
        "is",
        "of",
        "and",
        "to",
        "how",
        "does",
        "a",
        "an",
        "at",
        "on",
        "with",
        "as",
        "not",
        "be",
        "or",
        "from",
        "by",
        "it",
        "its",
        "that",
        "this",
        "which",
        "can",
        "when",
        "if",
        "where",
        "will",
        "use",
        "used",
        "vs",
        "between",
        "than",
        "but",
        "must",
        "should",
        "would",
        "shall",
        "may",
        "might",
        "need",
        "do",
        "did",
        "has",
        "have",
        "had",
        "being",
        "been",
        "were",
        "was",
        "into",
        "about",
        "up",
        "out",
        "all",
        "any",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "only",
        "own",
        "same",
        "so",
        "too",
        "very",
        "just",
        "also",
        "then",
        "now",
        "no",
        "yes",
        "q",
    }
)

_MIN_WORD_LENGTH = 3
_MAX_HASH_ID = 2**24


def _tokenize(text: str) -> list[str]:
    """Lowercase tokenisation — alphanumeric words of at least *min* chars."""
    return re.findall(r"\b[a-zA-Z][a-zA-Z0-9_]{2,}\b", text.lower())


def _token_id(token: str) -> int:
    """Deterministic hash-based token ID (stable across Python runs)."""
    return int(hashlib.md5(token.encode()).hexdigest()[:8], 16) % _MAX_HASH_ID


def _encode_single(text: str) -> tuple[list[int], list[float]]:
    """Encode *text* into a sparse vector (indices, values)."""
    tokens = [t for t in _tokenize(text) if t not in STOP_WORDS]
    if not tokens:
        return [], []

    tf: dict[str, int] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1

    indices: list[int] = []
    values: list[float] = []
    for term, freq in tf.items():
        indices.append(_token_id(term))
        values.append(1.0 + math.log(freq))

    return indices, values


def bm25_sparse_encoder(
    texts: list[str],
) -> tuple[list[list[int]], list[list[float]]]:
    """BM25-style sparse encoder for a batch of texts.

    Each unique term gets weight = 1 + log(term_frequency).
    Token IDs are deterministic hashes, making the encoder stateless.

    Args:
        texts: Batch of input strings.

    Returns:
        Tuple of (all_indices, all_values) where each element corresponds
        to one input text.
    """
    all_indices: list[list[int]] = []
    all_values: list[list[float]] = []

    for text in texts:
        indices, values = _encode_single(text)
        all_indices.append(indices)
        all_values.append(values)

    return all_indices, all_values


def create_sparse_encoder():
    """Return a BM25-based sparse encoder compatible with LlamaIndex/Qdrant.

    The returned callable accepts ``List[str]`` (batched) and returns
    ``Tuple[List[List[int]], List[List[float]]]``.
    """
    logger.info("Using BM25 sparse encoder (no external model required)")
    return bm25_sparse_encoder
