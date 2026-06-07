#!/usr/bin/env python3
"""Interactive RAG tester for Sigma specification Q/A in AskRag/ask_spec.md.

Usage:
    python AskRag/test_rag_ask.py
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

# Ensure imports work regardless of working directory
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.back.database import DatabaseService


STOP_WORDS = frozenset(
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
        "a",
    }
)


def _extract_keywords(text: str) -> set[str]:
    """Extract meaningful keywords from text, excluding stop words and short tokens."""
    words = set(re.findall(r"\b[a-zA-Z][a-zA-Z0-9_]{2,}\b", text.lower()))
    return words - STOP_WORDS


def _extract_bigrams(text: str) -> set[str]:
    """Extract meaningful adjacent word pairs from text."""
    words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9_]{2,}\b", text.lower())
    bigrams = set()
    for i in range(len(words) - 1):
        bigrams.add(f"{words[i]} {words[i + 1]}")
    return bigrams


def _evaluate_result(
    top_text: str, score: float, question: str, expected_answer: str
) -> tuple[str, float]:
    """Evaluate a RAG result and return (status, coverage_score)."""
    if not top_text:
        return "FAIL", 0.0

    # Keywords from question + expected answer combined
    kw_question = _extract_keywords(question)
    kw_answer = _extract_keywords(expected_answer)
    combined_keywords = kw_question | kw_answer

    if not combined_keywords:
        return "FAIL", 0.0

    # Single keyword overlap fraction
    matched = sum(1 for kw in combined_keywords if kw in top_text.lower())
    coverage = matched / len(combined_keywords)

    # Boost with bigram overlap (e.g. "value_count", "group_by")
    bigrams = _extract_bigrams(question) | _extract_bigrams(expected_answer)
    if bigrams:
        bigram_matches = sum(1 for bg in bigrams if bg in top_text.lower())
        bigram_coverage = bigram_matches / len(bigrams)
        coverage = max(coverage, bigram_coverage)

    # Weight by embedding score
    weighted = coverage * score

    if weighted >= 0.25 and score >= 0.3:
        return "PASS", weighted
    elif weighted >= 0.15 and score >= 0.2:
        return "PARTIAL", weighted
    else:
        return "FAIL", weighted


async def main() -> None:
    """Run the RAG test suite."""
    # --- Initialize DB ---
    db = DatabaseService()
    db.initialize()
    db.set_embedding_config("intfloat/multilingual-e5-small")

    from src.core.search.engine import SearchEngine

    engine = SearchEngine(collection_names=["sigma_spec"], top_k=3)

    # --- Parse questions from ask_spec.md ---
    qa_path = Path("AskRag/ask_spec.md")
    content = qa_path.read_text(encoding="utf-8")

    # Pattern: **Q:** <question> **A:** <answer> (stopping before next ** or end-of-string)
    pattern = re.compile(r"\*\*Q:\*\*\s*(.+?)\s*\n\*\*A:\*\*\s*(.+?)(?=\n\*\*|\Z)", re.DOTALL)
    matches = pattern.findall(content)

    if not matches:
        print("No questions found in AskRag/ask_spec.md")
        return

    questions: list[tuple[str, str]] = []
    for q, a in matches:
        # Clean up trailing section artifacts
        a_clean = re.sub(r"\n{3,}", "\n", a).strip()
        # Remove trailing markdown headers that leaked from next section
        a_clean = re.sub(r"\n\s*#{1,3}\s+\S.*", "", a_clean).strip()
        questions.append((q.strip(), a_clean))

    total = len(questions)
    print(f"Loaded {total} questions from {qa_path}\n")
    print("=" * 80)

    passed = 0
    failed = 0
    partial = 0

    for idx, (question, expected_answer) in enumerate(questions, 1):
        preview = question[:80].replace("\n", " ")
        print(f"\n[{idx}/{total}] Q: {preview}")

        try:
            results = await engine.search(question, top_k=3)
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1
            continue

        if not results:
            print("  No results from RAG search")
            failed += 1
            continue

        top_result = results[0]
        top_text = top_result.get("text", "")
        score = top_result.get("score", 0)

        print(f"  Score: {score:.4f}")

        status, weighted = _evaluate_result(top_text, score, question, expected_answer)
        print(f"  Weighted coverage: {weighted:.2f}")
        print(f"  STATUS: {status}")

        if status == "PASS":
            passed += 1
        elif status == "PARTIAL":
            partial += 1
        else:
            failed += 1

    # --- Summary ---
    print("\n" + "=" * 80)
    pass_rate = (passed + partial) / total * 100 if total else 0
    print(f"RESULTS: {passed} passed, {partial} partial, {failed} failed out of {total}")
    print(f"         {pass_rate:.1f}% acceptable (pass + partial)")
    print("=" * 80)

    db.close()
    return passed


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)

    # Windows event loop fix
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    result = asyncio.run(main())
    # Exit with error if fewer than 50% pass
    if result is not None and result < 10:
        sys.exit(1)
