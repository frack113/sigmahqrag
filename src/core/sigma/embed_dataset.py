import argparse
import json
from pathlib import Path
from typing import Any

import torch
import torch.nn.functional as F
from transformers import AutoModel, AutoTokenizer


def load_json_dataset(input_path: str | Path) -> list[dict[str, Any]]:
    """Charge un dataset JSON depuis un fichier.

    Args:
        - input_path (str | Path): Chemin du fichier JSON

    Returns:
        - list[dict[str, Any]]: Liste de lignes du dataset
    """
    input_path = Path(input_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Dataset not found: {input_path}")

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("Expected dataset JSON to be a list of rows.")

    return data


def get_text_to_embed(row: dict[str, Any]) -> str:
    """Extrait le texte a vectoriser depuis une ligne du dataset

    Args:
        - row (dict[str, Any]): Ligne du dataset

    Returns:
        - str: Texte sélectionné pour l'embedding
    """

    contexts = row.get("contexts", [])

    if isinstance(contexts, list) and contexts:
        return str(contexts[0])

    if row.get("ground_truth"):
        return str(row["ground_truth"])

    if row.get("question"):
        return str(row["question"])

    return ""


def mean_pooling(model_output: Any, attention_mask: torch.Tensor) -> torch.Tensor:
    """Calcule l'embedding moyen des tokens non masques

    Args:
        - model_output (Any): Sortie du modèle contenant les embeddings des tokens
        - attention_mask (torch.Tensor): Masque indiquant les tokens valides

    Returns:
        - torch.Tensor: Tensor contenant un embedding par texte
    """

    token_embeddings = model_output.last_hidden_state
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()

    return torch.sum(token_embeddings * input_mask_expanded, dim=1) / torch.clamp(
        input_mask_expanded.sum(dim=1),
        min=1e-9,
    )


def encode_texts(
    texts: list[str],
    model_name: str,
    batch_size: int = 32,
    max_length: int = 512,
    normalize: bool = True,
) -> list[list[float]]:
    """Encode une liste de textes en embeddings

    Args:
        - texts (list[str]): Textes à encoder
        - model_name (str): Nom du modele a utiliser
        - batch_size (int): Nombre de textes par batch
        - max_length (int): Longueur maximale des textes tokenises
        - normalize (bool): INdique si les embeddings doivent être normalises

    Returns:
        - list[list[float]]: Liste des embeddings generes
    """

    device = "cuda" if torch.cuda.is_available() else "cpu"

    print(f"Device: {device}")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModel.from_pretrained(model_name)
    model.to(device)
    model.eval()

    all_embeddings: list[list[float]] = []

    with torch.no_grad():
        for start in range(0, len(texts), batch_size):
            end = start + batch_size
            batch_texts = texts[start:end]

            encoded_input = tokenizer(
                batch_texts,
                padding=True,
                truncation=True,
                max_length=max_length,
                return_tensors="pt",
            )

            encoded_input = {key: value.to(device) for key, value in encoded_input.items()}

            model_output = model(**encoded_input)

            embeddings = mean_pooling(
                model_output,
                encoded_input["attention_mask"],
            )

            if normalize:
                embeddings = F.normalize(embeddings, p=2, dim=1)

            all_embeddings.extend(embeddings.cpu().tolist())

            print(f"Embedded {min(end, len(texts))}/{len(texts)}")

    return all_embeddings


def embed_dataset(
    dataset: list[dict[str, Any]],
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    batch_size: int = 32,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Ajoute des embeddings

    Args:
        - dataset (list[dict[str, Any]]): Dataset source a enrichir
        - model_name (str): Nom du modèle d'embedding a utiliser
        - batch_size (int): Nombre de lignes traitees par batch
        - limit (int | None): Nombre maximal de lignes a traiter

    Returns:
        - list[dict[str, Any]]: Dataset enrichi
    """

    if limit is not None:
        dataset = dataset[:limit]

    texts = [get_text_to_embed(row) for row in dataset]

    embeddings = encode_texts(
        texts=texts,
        model_name=model_name,
        batch_size=batch_size,
    )

    embedded_rows: list[dict[str, Any]] = []

    for row, embedding, text in zip(dataset, embeddings, texts, strict=True):
        embedded_rows.append(
            {
                **row,
                "embedding_text": text,
                "embedding_model": model_name,
                "embedding": embedding,
            }
        )

    return embedded_rows


def save_json_dataset(dataset: list[dict[str, Any]], output_path: str | Path) -> Path:
    """Sauvegarde un dataset au format JSON

    Args:
        - dataset (list[dict[str, Any]]): Dataset a sauvegarder
        - output_path (str | Path): Chemin du fichier de sortie

    Return:
        - Path: Chemin du fichier sauvegarde
    """

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False)

    return output_path


def embed_json_dataset_file(
    input_path: str | Path,
    output_path: str | Path,
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    batch_size: int = 32,
    limit: int | None = None,
) -> Path:
    """Charge, embedde et sauvegarde un dataset JSON

    Args:
        - input_path (str | Path): Chemin du dataset JSON source
        - output_path (str | Path): Chemin du dataset JSON enrichi a ecrire
        - model_name (str): Nom du modèle d'embedding
        - batch_size (int): Nombre de lignes traitees par batch
        - limit (int | None): Nombre maximal de lignes a traiter

    Returns:
        - Path: Chemin du fichier JSON
    """

    dataset = load_json_dataset(input_path)

    print(f"Loaded rows: {len(dataset)}")

    if limit is not None:
        print(f"Limit: {limit}")

    print(f"Embedding model: {model_name}")

    embedded_dataset = embed_dataset(
        dataset=dataset,
        model_name=model_name,
        batch_size=batch_size,
        limit=limit,
    )

    saved_path = save_json_dataset(embedded_dataset, output_path)

    print(f"Saved embedded dataset to: {saved_path}")
    print(f"Embedded rows: {len(embedded_dataset)}")

    return saved_path


def main() -> None:
    """Point d'entree CLI

    Returns:
        - None: Cette fonction ne retourne rien.
    """
    parser = argparse.ArgumentParser(description="Embed a RAGAS Sigma dataset and save it as JSON.")

    parser.add_argument(
        "--input",
        default="src/back/rag/transforms/sigma/ragas_dataset.json",
        help="Path to the input RAGAS dataset JSON.",
    )

    parser.add_argument(
        "--output",
        default="src/back/rag/transforms/sigma/dataset_embedded.json",
        help="Path to the output embedded dataset JSON.",
    )

    parser.add_argument(
        "--model",
        default="sentence-transformers/all-MiniLM-L6-v2",
        help="Hugging Face embedding model name.",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Embedding batch size.",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of rows to embed. Useful for tests.",
    )

    args = parser.parse_args()

    embed_json_dataset_file(
        input_path=args.input,
        output_path=args.output,
        model_name=args.model,
        batch_size=args.batch_size,
        limit=args.limit,
    )


if __name__ == "__main__":
    main()
