"""Search quality evaluation infrastructure.

Provides golden set management, recall/precision metrics, evaluation runner,
and exact-search baseline comparison for Qdrant hybrid search tuning.
"""

from src.core.search.eval.golden_set import GoldenQuery, GoldenSet, load_golden_set, save_golden_set
from src.core.search.eval.metrics import (
    context_precision,
    context_recall,
    mean_reciprocal_rank,
    recall_at_k,
)
from src.core.search.eval.runner import SearchEvaluator
from src.core.search.eval.exact_search import compare_exact_vs_approximate

__all__ = [
    "GoldenQuery",
    "GoldenSet",
    "load_golden_set",
    "save_golden_set",
    "recall_at_k",
    "mean_reciprocal_rank",
    "context_precision",
    "context_recall",
    "SearchEvaluator",
    "compare_exact_vs_approximate",
]
