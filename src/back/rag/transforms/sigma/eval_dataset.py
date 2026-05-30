import json
from pathlib import Path


def build_ragas_dataset(chunks: list[dict]) -> list[dict]:
    """Construit le dataset"""
    rows: list[dict] = []

    for chunk in chunks:
        questions = chunk.get("eval_questions", [])

        if not questions:
            questions = [f"What information is contained in this {chunk['chunk_type']} chunk?"]

        for question in questions:
            rows.append(
                {
                    "question": question,
                    "ground_truth": chunk["ground_truth"],
                    "contexts": [chunk["text"]],
                    "metadata": chunk["metadata"],
                }
            )

    return rows


def save_ragas_dataset_json(dataset: list[dict], output_path: str | Path) -> Path:
    """Sauvegarde dataset"""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    return output_path
