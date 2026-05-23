"""Embedder — delegates to config-driven HuggingFaceEmbedding via ingestion builder."""

from __future__ import annotations

from src.back.rag.ingestion import DEFAULT_MODEL, build_embed_model


class Embedder:
    """Document embedder using config-driven HuggingFaceEmbedding."""

    def __init__(self, model_name: str = DEFAULT_MODEL) -> None:
        self._model = build_embed_model(model_name)

    def embed(self, text: str) -> list[float]:
        return self._model.get_text_embedding(text)  # type: ignore[no-any-return]

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return self._model.get_text_embedding_batch(texts)  # type: ignore[no-any-return]
