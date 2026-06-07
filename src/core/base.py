"""Base contract for format-specific document transforms."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from llama_index.core.schema import Document


@dataclass
class TransformConfig:
    """Shared configuration for all transforms.

    Attributes:
        collection_name: Target Qdrant collection name.
        model_name: HuggingFace embedding model name.
        chunk_size: Max tokens per chunk (for formats using SentenceSplitter).
        chunk_overlap: Tokens of overlap between adjacent chunks.
        batch_size: Number of documents per embedding batch.
        max_length: Max token length for the embedding model.
        enable_sbert: Use sentence-transformers for embedding.
        enable_eval_questions: Generate eval questions for RAGAS evaluation.
        llm_client: Optional LLM client for keyword generation.
    """

    collection_name: str = "default"
    collection: str = "default"
    model_name: str = "intfloat/multilingual-e5-small"
    chunk_size: int = 1024
    chunk_overlap: int = 100
    batch_size: int = 8
    max_length: int = 512
    enable_sbert: bool = True
    enable_eval_questions: bool = False
    llm_client: Any = None
    max_heading_level: int = 3
    """Max heading depth for markdown chunking (1=H1 only, 2=H1+H2, 3=H1+H2+H3)."""


class DocumentTransform(ABC):
    """Base class all format-specific transforms must implement.

    Pipeline::

        parse(file) → process(documents) → output(documents) → post_process(documents)

    * ``parse`` — abstract, loads raw file content.
    * ``process`` — abstract, chunking + enrichment in a single pass.
    * ``output`` — optional formatting/filtering (identity by default).
    * ``post_process`` — optional cross-cutting (identity by default).

    The base provides an implementation of ``process()`` that decomposes
    into two protected hooks::

        def process(self, documents):
            chunks = self._chunk(documents)
            return self._enrich(chunks)

    Simple transforms (PDF, Office, Generic) override ``_chunk()``.
    Complex transforms (Sigma, Markdown) override ``process()`` directly.
    ``_enrich()`` is overridden only when enrichment must differ from
    ``enrich_by_llm``.
    """

    FORMAT_NAME: str = ""
    """Human-readable format name (e.g. 'sigma', 'pdf', 'markdown')."""

    SUPPORTED_EXTENSIONS: tuple[str, ...] = ()
    """File extensions this transform handles (e.g. ('.yml', '.yaml'))."""

    def __init__(self, config: TransformConfig | None = None) -> None:
        self.config = config or self._build_default_config()

    # ------------------------------------------------------------------
    # Pipeline stages
    # ------------------------------------------------------------------

    @abstractmethod
    def parse(self, file_path: Path) -> list[Document]:
        """Convert raw file content to LlamaIndex Document objects.

        Must set ``source_file``, ``doc_type``, and ``file_name`` in metadata.

        Args:
            file_path: Path to the source file.

        Returns:
            List of Document objects (one or more per file).
        """

    def process(self, documents: list[Document]) -> list[Document]:
        """Chunk and enrich documents in a single pass.

        The default implementation calls ``_chunk()`` then ``_enrich()``.
        Override directly when chunking and enrichment are intertwined
        (e.g. Sigma, Markdown).

        Args:
            documents: List of Document objects from ``parse()``.

        Returns:
            List of chunked and enriched Document objects.
        """
        chunks = self._chunk(documents)
        return self._enrich(chunks)

    def output(self, documents: list[Document]) -> list[Document]:
        """Optional formatting/filtering before storage.

        Args:
            documents: List of Document objects from ``process()``.

        Returns:
            Processed Document objects.
        """
        return documents

    def post_process(self, documents: list[Document]) -> list[Document]:
        """Optional cross-cutting meta-operations (eval questions, tags, etc.).

        Args:
            documents: List of Document objects from ``output()``.

        Returns:
            Processed Document objects.
        """
        return documents

    # ------------------------------------------------------------------
    # Protected hooks (used by the default ``process()``)
    # ------------------------------------------------------------------

    def _chunk(self, documents: list[Document]) -> list[Document]:
        """Split documents into chunks (SentenceSplitter by default).

        Override for formats with custom chunking logic.  Must NOT
        perform enrichment.

        Args:
            documents: List of Document objects from ``parse()``.

        Returns:
            List of chunked Document objects.
        """
        from llama_index.core.node_parser import SentenceSplitter

        splitter = SentenceSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        return splitter(documents)  # type: ignore[return-value]

    def _enrich(self, documents: list[Document]) -> list[Document]:
        """Enrich each chunk with LLM-generated summary and keywords.

        Calls ``generique.llm.enrich_by_llm`` for every non-empty chunk.
        Override only when enrichment logic must differ.

        Args:
            documents: List of Document objects from ``_chunk()``.

        Returns:
            Enriched Document objects.
        """
        from .document.llm import enrich_by_llm

        llm_client = getattr(self.config, "llm_client", None)
        updated: list[Document] = []
        for doc in documents:
            text = doc.text or ""
            if not text.strip():
                updated.append(doc)
                continue
            result = (
                enrich_by_llm(text, llm_client)
                if llm_client
                else {"summary": None, "keywords": None}
            )
            summary = result.get("summary") or ""
            keywords = result.get("keywords") or ""
            if summary or keywords:
                enrichment = "\n\n---\n"
                if summary:
                    enrichment += f"Summary: {summary}\n\n"
                if keywords:
                    enrichment += f"Keywords: {keywords}\n"
                doc = Document(
                    text=text + enrichment,
                    metadata={**doc.metadata, "has_llm_enrichment": True},
                    excluded_embed_metadata_keys=doc.excluded_embed_metadata_keys,
                )
            else:
                doc = Document(
                    text=text,
                    metadata={**doc.metadata, "has_llm_enrichment": False},
                    excluded_embed_metadata_keys=doc.excluded_embed_metadata_keys,
                )
            updated.append(doc)
        return updated

    # ------------------------------------------------------------------
    # Pipeline execution
    # ------------------------------------------------------------------

    def run(self, file_path: Path) -> list[Document]:
        """Execute the full pipeline: parse → process → output → post_process.

        **Do not override** — place custom logic in the individual stages.

        Injects ``collection`` into each document's metadata.

        Args:
            file_path: Path to the source file.

        Returns:
            List of Document objects ready for embedding/indexing.
        """
        documents = self.parse(file_path)
        assert documents, f"{type(self).__name__}.parse() returned empty list"
        assert "source_file" in documents[0].metadata, "parse() must set source_file in metadata"
        assert "doc_type" in documents[0].metadata, "parse() must set doc_type in metadata"
        assert "file_name" in documents[0].metadata, "parse() must set file_name in metadata"

        documents = self.process(documents)
        assert documents, f"{type(self).__name__}.process() returned empty list"
        assert "chunk_type" in documents[0].metadata, "process() must set chunk_type in metadata"

        documents = self.output(documents)
        documents = self.post_process(documents)

        for doc in documents:
            doc.metadata["collection"] = self.config.collection
        return documents

    # ------------------------------------------------------------------
    # Resolution helpers
    # ------------------------------------------------------------------

    @classmethod
    def _build_default_config(cls) -> TransformConfig:
        """Build default config from Config."""
        from src.config.settings import get_config

        cfg = get_config()
        collection_name = getattr(cfg, "qdrant_collection_name", "default")
        return TransformConfig(
            collection_name=collection_name,
            collection=collection_name,
            model_name=getattr(cfg, "embedding_model_name", "intfloat/multilingual-e5-small"),
            chunk_size=getattr(cfg, "chunk_size", 1024),
            chunk_overlap=getattr(cfg, "chunk_overlap", 100),
            enable_sbert=getattr(cfg, "enable_sbert", True),
            enable_eval_questions=getattr(cfg, "enable_eval_questions", False),
        )

    @classmethod
    def can_handle(cls, file_path: Path | str) -> bool:
        """Check if this transform can handle the given file.

        Uses ``SUPPORTED_EXTENSIONS`` for format detection.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if this transform can handle the file.
        """
        path = Path(file_path)
        return path.suffix.lower() in cls.SUPPORTED_EXTENSIONS
