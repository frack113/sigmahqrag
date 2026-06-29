"""Test RAG simplifié sans serveur FastAPI."""

import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.core.search.engine import SearchEngine
from AskRag.test_rag_ask import _bootstrap_infra, _extract_keywords, _extract_bigrams


def _evaluate_result(top_text: str, score: float, question: str, expected_answer: str):
    if not top_text:
        return "FAIL", 0.0
    kw_question = _extract_keywords(question)
    kw_answer = _extract_keywords(expected_answer)
    combined_keywords = kw_question | kw_answer
    if not combined_keywords:
        return "FAIL", 0.0
    matched = sum(1 for kw in combined_keywords if kw in top_text.lower())
    coverage = matched / len(combined_keywords)
    bigrams = _extract_bigrams(question) | _extract_bigrams(expected_answer)
    if bigrams:
        bigram_matches = sum(1 for bg in bigrams if bg in top_text.lower())
        bigram_coverage = bigram_matches / len(bigrams)
        coverage = max(coverage, bigram_coverage)
    weighted = coverage * score
    if weighted >= 0.25 and score >= 0.3:
        return "PASS", weighted
    elif weighted >= 0.15 and score >= 0.2:
        return "PARTIAL", weighted
    else:
        return "FAIL", weighted


async def main():
    # Bootstrap DuckDB
    _bootstrap_infra()

    # Créer le moteur de recherche
    engine = SearchEngine(collection_names=["sigma_spec"], top_k=3)

    # Charger les questions
    qa_path = Path("AskRag/ask_spec.md")
    content = qa_path.read_text(encoding="utf-8")

    pattern = re.compile(r"\*\*Q:\*\*\s*(.+?)\s*\n\*\*A:\*\*\s*(.+?)(?=\n\*\*|\Z)", re.DOTALL)
    matches = pattern.findall(content)

    questions = []
    for q, a in matches:
        a_clean = re.sub(r"\n{3,}", "\n", a).strip()
        a_clean = re.sub(r"\n\s*#{1,3}\s+\S.*", "", a_clean).strip()
        questions.append((q.strip(), a_clean))

    print(f"Total questions: {len(questions)}\n")

    # Tester chaque question
    passed = 0
    failed = 0
    partial = 0
    total_weighted = 0

    for i, (q, a) in enumerate(questions):
        try:
            results = await engine.search(q, top_k=3)
            if not results:
                status = "FAIL"
                weighted = 0.0
            else:
                # Prendre le meilleur résultat
                best = max(results, key=lambda r: r.get("score", 0))
                top_text = best["text"]
                score = best["score"]
                status, weighted = _evaluate_result(top_text, score, q, a)

                if status == "FAIL":
                    print(f"Q{i + 1}: {q[:80]}...")
                    print(f"  Text: {top_text[:150]}...")
                    print(f"  Score: {score:.3f}, Weighted: {weighted:.3f}")
                    print()
        except Exception as e:
            status = "FAIL"
            weighted = 0.0
            print(f"Q{i + 1}: Error: {e}")

        if status == "PASS":
            passed += 1
        elif status == "PARTIAL":
            partial += 1
        else:
            failed += 1

        total_weighted += weighted

    print("=" * 80)
    print("Résultats:")
    print(f"  PASS: {passed}/{len(questions)} ({passed / len(questions) * 100:.1f}%)")
    print(f"  PARTIAL: {partial}/{len(questions)}")
    print(f"  FAIL: {failed}/{len(questions)}")
    print(f"  Score moyen: {total_weighted / len(questions):.3f}")


if __name__ == "__main__":
    asyncio.run(main())
