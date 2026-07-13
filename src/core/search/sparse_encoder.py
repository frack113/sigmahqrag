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

# BM25 default parameters
_K1 = 1.2
_B = 0.75


def _tokenize(text: str) -> list[str]:
    """Lowercase tokenisation — alphanumeric words of at least *min* chars."""
    return re.findall(r"\b[a-zA-Z][a-zA-Z0-9_]{2,}\b", text.lower())


def _token_id(token: str) -> int:
    """Deterministic hash-based token ID (stable across Python runs)."""
    return int(hashlib.md5(token.encode()).hexdigest()[:8], 16) % _MAX_HASH_ID


def _tf_weight(freq: int) -> float:
    """Sublinear TF saturation with BM25's k1."""
    return (_K1 + 1.0) * freq / (_K1 + freq)


def _encode_single(
    text: str,
    idf_map: dict[str, float] | None = None,
    avg_doc_len: float | None = None,
) -> tuple[list[int], list[float]]:
    """Encode *text* into a sparse vector (indices, values).

    When ``idf_map`` is provided, weights are BM25-style:
        ``score = IDF * (k1 + 1) * tf / (k1 * (1 - b + b * Ld / Lavg) + tf)``

    Otherwise falls back to sublinear TF (``1 + log(tf)``).
    """
    tokens = [t for t in _tokenize(text) if t not in STOP_WORDS]
    if not tokens:
        return [], []

    tf: dict[str, int] = {}
    for t in tokens:
        tf[t] = tf.get(t, 0) + 1

    doc_len = len(tokens)
    length_norm = 1.0
    if avg_doc_len is not None and avg_doc_len > 0:
        length_norm = 1.0 - _B + _B * (doc_len / avg_doc_len) * _K1

    indices: list[int] = []
    values: list[float] = []
    for term, freq in tf.items():
        if idf_map is not None:
            idf = idf_map.get(term, 1.5)
            bm25_score = idf * _tf_weight(freq) / (length_norm + freq)
            values.append(bm25_score)
        else:
            values.append(1.0 + math.log(freq))
        indices.append(_token_id(term))

    return indices, values


class IDFCalculator:
    """Accumulates corpus-level term frequencies to compute IDF.

    Usage:
        calc = IDFCalculator()
        for text in corpus:
            calc.add_document(text)
        idf_map = calc.idf()
    """

    def __init__(self) -> None:
        self._df: dict[str, int] = {}
        self._num_docs: int = 0

    def add_document(self, text: str) -> int:
        """Add a single document to the corpus. Returns token count."""
        tokens = set(_tokenize(text))
        tokens.discard("")
        for t in tokens:
            self._df[t] = self._df.get(t, 0) + 1
        self._num_docs += 1
        return len(tokens)

    def idf(self, smooth: bool = True) -> dict[str, float]:
        """Return ``{term: idf}`` map using BM25's IDF formula.

        With smoothing: ``idf = log(1 + (N - df + 0.5) / (df + 0.5))``
        """
        n = self._num_docs
        if n == 0:
            return {}
        if smooth:
            return {t: math.log(1.0 + (n - df + 0.5) / (df + 0.5)) for t, df in self._df.items()}
        return {t: math.log(n / df) for t, df in self._df.items()}


def bm25_sparse_encoder(
    texts: list[str],
) -> tuple[list[list[int]], list[list[float]]]:
    """TF-only sparse encoder for a batch of texts.

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


def bm25_idf_sparse_encoder(
    texts: list[str],
    *,
    idf_map: dict[str, float],
    avg_doc_len: float,
) -> tuple[list[list[int]], list[list[float]]]:
    """Full BM25 sparse encoder with IDF + document length normalisation.

    Args:
        texts: Batch of input strings.
        idf_map: Pre-computed ``{term: idf}`` map.
        avg_doc_len: Average document length for length normalisation.

    Returns:
        Tuple of (all_indices, all_values) where each element corresponds
        to one input text.
    """
    all_indices: list[list[int]] = []
    all_values: list[list[float]] = []

    for text in texts:
        indices, values = _encode_single(text, idf_map=idf_map, avg_doc_len=avg_doc_len)
        all_indices.append(indices)
        all_values.append(values)

    return all_indices, all_values


def create_sparse_encoder():
    """Return a TF-based sparse encoder compatible with LlamaIndex/Qdrant.

    The returned callable accepts ``List[str]`` (batched) and returns
    ``Tuple[List[List[int]], List[List[float]]]``.
    """
    logger.info("Using BM25 sparse encoder (no external model required)")
    return bm25_sparse_encoder
