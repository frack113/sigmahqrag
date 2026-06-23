from pathlib import Path
import re
import requests
from typing import TypedDict


INPUT_FILE = Path("./ask_spec.md")
OLLAMA_EMBED_URL = "http://localhost:11434/api/embed"
EMBED_MODEL = "mxbai-embed-large"


class Chunk(TypedDict):
    chunk_type: str
    title: str
    text: str
    metadata: dict


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def chunk_by_h2(text: str) -> list[Chunk]:
    pattern = re.compile(
        r"^##\s+(.+?)\s*$",
        re.MULTILINE,
    )

    matches = list(pattern.finditer(text))
    chunks: list[Chunk] = []

    for i, match in enumerate(matches):
        section_title = match.group(1).strip()
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

        section_text = text[start:end].strip()

        chunks.append(
            {
                "chunk_type": "h2_section",
                "title": section_title,
                "text": section_text,
                "metadata": {
                    "section_level": "h2",
                    "section_title": section_title,
                    "chunk_index": i,
                },
            }
        )

    return chunks


def extract_current_h2(text_before: str) -> str | None:
    h2_titles = re.findall(
        r"^##\s+(.+?)\s*$",
        text_before,
        flags=re.MULTILINE,
    )

    return h2_titles[-1].strip() if h2_titles else None


def extract_current_h3(text_before: str) -> str | None:
    h3_titles = re.findall(
        r"^###\s+(.+?)\s*$",
        text_before,
        flags=re.MULTILINE,
    )

    return h3_titles[-1].strip() if h3_titles else None


def chunk_by_qa(text: str) -> list[Chunk]:
    pattern = re.compile(
        r"\*\*Q:\*\*\s*(?P<question>.*?)\n"
        r"\*\*A:\*\*\s*(?P<answer>.*?)(?=\n\*\*Q:\*\*|\n###\s+|\n##\s+|\Z)",
        re.DOTALL,
    )

    chunks: list[Chunk] = []

    for i, match in enumerate(pattern.finditer(text)):
        question = match.group("question").strip()
        answer = match.group("answer").strip()

        text_before = text[: match.start()]
        h2 = extract_current_h2(text_before)
        h3 = extract_current_h3(text_before)

        chunk_text = f"Question: {question}\nAnswer: {answer}"

        chunks.append(
            {
                "chunk_type": "qa_pair",
                "title": question,
                "text": chunk_text,
                "metadata": {
                    "question": question,
                    "answer": answer,
                    "h2_section": h2,
                    "h3_section": h3,
                    "chunk_index": i,
                },
            }
        )

    return chunks


def embed_text(text: str) -> list[float]:
    response = requests.post(
        OLLAMA_EMBED_URL,
        json={
            "model": EMBED_MODEL,
            "input": text,
        },
        timeout=60,
    )

    response.raise_for_status()

    result = response.json()

    return result["embeddings"][0]


def embed_chunks(chunks: list[Chunk]) -> list[dict]:
    embedded_chunks = []

    for chunk in chunks:
        adjusted_prompt = chunk["text"]

        embedding = embed_text(adjusted_prompt)

        embedded_chunks.append(
            {
                "chunk": chunk,
                "embedding": embedding,
            }
        )

    return embedded_chunks


def main() -> None:
    text = read_text(INPUT_FILE)

    # Liste 1 : chunks par sections H2
    h2_chunks = chunk_by_h2(text)

    # Liste 2 : chunks question/réponse
    qa_chunks = chunk_by_qa(text)

    print(f"H2 chunks: {len(h2_chunks)}")
    print(f"QA chunks: {len(qa_chunks)}")

    # Envoi des chunks H2 à Ollama
    h2_embeddings = embed_chunks(h2_chunks)

    # Envoi des chunks Q/A à Ollama
    qa_embeddings = embed_chunks(qa_chunks)

    print(f"H2 embeddings: {len(h2_embeddings)}")
    print(f"QA embeddings: {len(qa_embeddings)}")

    # Exemple : afficher la dimension du premier embedding
    if h2_embeddings:
        print("Dimension embedding H2:", len(h2_embeddings[0]["embedding"]))

    if qa_embeddings:
        print("Dimension embedding QA:", len(qa_embeddings[0]["embedding"]))


if __name__ == "__main__":
    main()