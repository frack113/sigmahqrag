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


async def main() -> None:
    # --- Initialize DB ---
    db = DatabaseService()
    db.initialize()
    db.set_embedding_config("intfloat/multilingual-e5-small")

    from src.back.rag.search import SearchEngine

    engine = SearchEngine(collection_names=["sigma_spec"], top_k=3)

    # --- Parse questions from ask_spec.md ---
    qa_path = Path("AskRag/ask_spec.md")
    content = qa_path.read_text(encoding="utf-8")

    pattern = re.compile(r"\*\*Q:\*\*\s*(.+?)\s*\n\*\*A:\*\*\s*(.+?)(?=\n\*\*|\Z)", re.DOTALL)
    matches = pattern.findall(content)

    if not matches:
        print("No questions found in AskRag/ask_spec.md")
        return

    questions = []
    for q, a in matches:
        # Clean up answer (trim trailing section headers that leaked in)
        a_clean = re.sub(r"\n{2,}", "\n", a).strip()
        # Remove trailing ### or ## headers that leaked from next section
        a_clean = re.sub(r"\n\s*#{1,3}\s+\S", "", a_clean).strip()
        questions.append((q.strip(), a_clean))

    print(f"Loaded {len(questions)} questions from {qa_path}\n")
    print("=" * 80)

    passed = 0
    failed = 0
    partial = 0

    for idx, (question, expected_answer) in enumerate(questions, 1):
        print(f"\n[{idx}/{len(questions)}] Q: {question[:80]}")

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

        # Check if answer keywords appear in top result
        keywords = set(re.findall(r"\b\w+\b", question.lower()))
        # Remove stop words
        stop_words = {
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
            "are",
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
            "than",
            "too",
            "very",
            "just",
            "also",
            "then",
            "now",
            "or",
            "and",
            "but",
            "not",
            "no",
            "yes",
            "q",
            "a",
        }
        meaningful_keywords = keywords - stop_words
        meaningful_keywords = {kw for kw in meaningful_keywords if len(kw) > 2}

        # Also check expected answer keywords
        answer_keywords = set(re.findall(r"\b\w+\b", expected_answer.lower())) - stop_words
        answer_keywords = {kw for kw in answer_keywords if len(kw) > 2}

        combined_keywords = meaningful_keywords | answer_keywords

        # Count how many keywords appear in the top result
        matched = sum(1 for kw in combined_keywords if kw in top_text.lower())
        coverage = matched / len(combined_keywords) if combined_keywords else 0
        # Adjust for low score
        coverage *= score

        print(f"  Keyword coverage: {coverage:.2f}")

        # Adjusted thresholds: embedding score is strong indicator,
        # keyword coverage is secondary (chunks may use synonyms)
        if coverage >= 0.25 and score >= 0.3:
            print("  STATUS: PASS")
            passed += 1
        elif coverage >= 0.15 and score >= 0.2:
            print("  STATUS: PARTIAL")
            partial += 1
        else:
            print("  STATUS: FAIL")
            failed += 1

    # --- Summary ---
    print("\n" + "=" * 80)
    print(f"RESULTS: {passed} passed, {partial} partial, {failed} failed out of {len(questions)}")
    print("=" * 80)

    db.close()
    return passed


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.WARNING)

    # Windows event loop fix
    import sys

    if sys.platform == "win32":
        import asyncio

        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    result = asyncio.run(main())
    if result and result < 10:  # If less than 10 passed, exit with error
        sys.exit(1)
