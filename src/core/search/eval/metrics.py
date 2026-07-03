"""Retrieval quality metrics for search evaluation.

Implements standard information retrieval metrics:
- ``recall_at_k``: fraction of relevant docs found in top-k
- ``precision_at_k``: fraction of top-k results that are relevant
- ``mean_reciprocal_rank``: average of 1/rank of first relevant result
- ``context_precision``: weighted precision by position (AP-style)
- ``context_recall``: recall estimated via retrieved contexts vs ground truth
"""

from __future__ import annotations


def recall_at_k(retrieved_ids: list[str], relevant_ids: list[str], k: int | None = None) -> float:
    """Fraction of relevant documents found in the top-k retrieved results.

    Args:
        retrieved_ids: Document IDs returned by the retriever, in rank order.
        relevant_ids: Ground-truth relevant document IDs.
        k: Number of results to consider.  Defaults to ``len(retrieved_ids)``.

    Returns:
        Recall score in ``[0.0, 1.0]``.  Returns ``0.0`` if no relevant docs
        are known (avoids division by zero).
    """
    if not relevant_ids:
        return 0.0
    cutoff = retrieved_ids[:k] if k is not None else retrieved_ids
    hits = sum(1 for doc_id in cutoff if doc_id in relevant_ids)
    return hits / len(relevant_ids)


def precision_at_k(
    retrieved_ids: list[str], relevant_ids: list[str], k: int | None = None
) -> float:
    """Fraction of top-k retrieved results that are relevant.

    Args:
        retrieved_ids: Document IDs returned by the retriever, in rank order.
        relevant_ids: Ground-truth relevant document IDs.
        k: Number of results to consider.  Defaults to ``len(retrieved_ids)``.

    Returns:
        Precision score in ``[0.0, 1.0]``.  Returns ``0.0`` if k=0.
    """
    cutoff = retrieved_ids[:k] if k is not None else retrieved_ids
    if not cutoff:
        return 0.0
    hits = sum(1 for doc_id in cutoff if doc_id in relevant_ids)
    return hits / len(cutoff)


def mean_reciprocal_rank(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """Mean Reciprocal Rank — average of ``1/rank`` for the first relevant doc.

    If no relevant document appears in the retrieved list, returns ``0.0``.

    Args:
        retrieved_ids: Document IDs returned by the retriever, in rank order.
        relevant_ids: Ground-truth relevant document IDs.

    Returns:
        MRR score in ``[0.0, 1.0]``.
    """
    relevant_set = set(relevant_ids)
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_set:
            return 1.0 / rank
    return 0.0


def average_precision(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """Average Precision — precision averaged at each relevant document position.

    Args:
        retrieved_ids: Document IDs returned by the retriever, in rank order.
        relevant_ids: Ground-truth relevant document IDs.

    Returns:
        AP score in ``[0.0, 1.0]``.  Returns ``0.0`` if no relevant docs.
    """
    if not relevant_ids:
        return 0.0
    relevant_set = set(relevant_ids)
    hits = 0
    precision_sum = 0.0
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_set:
            hits += 1
            precision_sum += hits / rank
    return precision_sum / len(relevant_ids)


def context_precision(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """Position-weighted precision (similar to AP but normalised by min(k, |relevant|)).

    Unlike AP which divides by ``|relevant_ids|``, this divides by the number of
    relevant docs that actually appear in the retrieved list (or all relevant
    docs if they all appear), giving a score in ``[0, 1]`` even when only a
    subset of relevant docs is retrieved.

    Args:
        retrieved_ids: Document IDs returned by the retriever, in rank order.
        relevant_ids: Ground-truth relevant document IDs.

    Returns:
        Context precision score in ``[0.0, 1.0]``.
    """
    if not retrieved_ids or not relevant_ids:
        return 0.0
    relevant_set = set(relevant_ids)
    weighted_sum = 0.0
    for rank, doc_id in enumerate(retrieved_ids, start=1):
        if doc_id in relevant_set:
            weighted_sum += 1.0 / rank
    divisor = min(len(retrieved_ids), len(relevant_ids))
    return weighted_sum / divisor


def context_recall(retrieved_ids: list[str], relevant_ids: list[str]) -> float:
    """Estimates recall from the retriever's perspective.

    Measures what fraction of known relevant documents the retriever actually
    returned.  This is the standard recall@all (k = full retrieved list).

    Args:
        retrieved_ids: Document IDs returned by the retriever.
        relevant_ids: Ground-truth relevant document IDs.

    Returns:
        Context recall score in ``[0.0, 1.0]``.
    """
    if not relevant_ids:
        return 0.0
    retrieved_set = set(retrieved_ids)
    hits = sum(1 for doc_id in relevant_ids if doc_id in retrieved_set)
    return hits / len(relevant_ids)


def evaluate_query(
    retrieved_ids: list[str],
    relevant_ids: list[str],
    k: int | None = None,
) -> dict[str, float]:
    """Compute all metrics for a single query.

    Args:
        retrieved_ids: Document IDs returned by the retriever, in rank order.
        relevant_ids: Ground-truth relevant document IDs.
        k: Optional cutoff for recall@k and precision@k.

    Returns:
        Dict with keys: ``recall_at_k``, ``precision_at_k``, ``mrr``,
        ``average_precision``, ``context_precision``, ``context_recall``.
    """
    return {
        "recall_at_k": recall_at_k(retrieved_ids, relevant_ids, k),
        "precision_at_k": precision_at_k(retrieved_ids, relevant_ids, k),
        "mrr": mean_reciprocal_rank(retrieved_ids, relevant_ids),
        "average_precision": average_precision(retrieved_ids, relevant_ids),
        "context_precision": context_precision(retrieved_ids, relevant_ids),
        "context_recall": context_recall(retrieved_ids, relevant_ids),
    }


def aggregate_metrics(metrics_list: list[dict[str, float]]) -> dict[str, float]:
    """Average a list of per-query metric dicts.

    Args:
        metrics_list: Per-query results from :func:`evaluate_query`.

    Returns:
        Dict of mean metric values.
    """
    if not metrics_list:
        return {}
    keys = metrics_list[0].keys()
    return {key: sum(m[key] for m in metrics_list) / len(metrics_list) for key in keys}
