"""Base contract for format-specific document transforms."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from llama_index.core.schema import Document

if TYPE_CHECKING:
    pass


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
        enable_rich_chunks: Skip LlamaIndex SentenceSplitter for pre-chunked output.
        enable_eval_questions: Generate eval questions for RAGAS evaluation.
    """

    collection_name: str = "default"
    model_name: str = "intfloat/multilingual-e5-small"
    chunk_size: int = 1024
    chunk_overlap: int = 100
    batch_size: int = 8
    max_length: int = 512
    enable_sbert: bool = True
    enable_rich_chunks: bool = False
    enable_eval_questions: bool = False


@dataclass
class ChunkMetadata:
    """Metadata attached to a Document before chunking.

    Attributes:
        source_file: Path to the original source file.
        doc_type: Type of document being processed (e.g. 'sigma_rule').
        rule_id: Sigma rule ID if applicable.
        rule_meta: Sigma rule metadata dict if applicable.
    """

    source_file: Path
    doc_type: str
    rule_id: str | None = None
    rule_meta: dict | None = None


@dataclass
class ChunkedDocument:
    """A single chunk resulting from the chunk() stage.

    Attributes:
        content: The text content of the chunk.
        metadata: Structured metadata for the chunk.
        chunk_type: Category of chunk (e.g. 'summary', 'mapping').
        source_file: Path to the original source file.
        rule_id: Sigma rule ID if applicable.
        eval_questions: Optional list of eval questions for RAGAS.
    """

    content: str
    metadata: dict
    chunk_type: str = "default"
    source_file: Path | None = None
    rule_id: str | None = None
    eval_questions: list[str] | None = None

    def to_document(self) -> Document:
        """Convert to LlamaIndex Document with embedding disabled if rich chunks enabled."""
        return Document(
            text=self.content,
            metadata={
                **self.metadata,
                "chunk_type": self.chunk_type,
                "source_file": str(self.source_file) if self.source_file else None,
                "rule_id": self.rule_id,
                "_eval_questions": self.eval_questions,
            },
            excluded_llm_metadata_keys=["\n", "chunk_type", "source_file", "rule_id"],
            excluded_embed_metadata_keys=["\n", "chunk_type", "source_file", "rule_id"]
            if _rich_chunks_enabled()
            else [],
        )


def _rich_chunks_enabled() -> bool:
    """Check if rich chunking is globally enabled."""
    from src.shared.config import get_config

    config = get_config()
    # Default to False if not configured
    return getattr(config, "enable_rich_chunks", False)


class DocumentTransform(ABC):
    """Base class all format-specific transforms must implement.

    A transform has three stages:
    1. **parse** -- load raw file content into LlamaIndex Document objects.
       One file may contain multiple documents (e.g. a YAML with several Sigma rules).
    2. **chunk** -- split Document objects into appropriately-sized chunks.
       Formats with rich chunking (e.g. Sigma) produce more chunks per document.
       Formats without rich chunking return the documents as-is.
    3. **post_process** -- optional final step (e.g. adding eval questions).
       Default is identity.
    """

    FORMAT_NAME: str = ""
    """Human-readable format name (e.g. 'sigma_rules', 'pdf', 'docx')."""

    SUPPORTED_EXTENSIONS: tuple[str, ...] = ()
    """File extensions this transform handles (e.g. ('.yml', '.yaml'))."""

    def __init__(self, config: TransformConfig | None = None) -> None:
        self.config = config or self._build_default_config()

    @abstractmethod
    def parse(self, file_path: Path) -> list[Document]:
        """Convert raw file content to LlamaIndex Document objects.

        Args:
            file_path: Path to the source file.

        Returns:
            List of Document objects (one or more per file).
        """

    @abstractmethod
    def chunk(self, documents: list[Document]) -> list[Document]:
        """Transform Document objects into chunks suitable for embedding.

        Can return the same documents unchanged (for formats that rely on the
        LlamaIndex SentenceSplitter) or produce multiple chunks per document
        (for rich chunking formats like Sigma).

        Args:
            documents: List of Document objects from parse().

        Returns:
            List of Document objects ready for embedding/indexing.
        """

    def post_process(self, documents: list[Document]) -> list[Document]:
        """Optional post-processing step after chunking.

        Default implementation returns documents unchanged. Subclasses can
        override to add eval questions, additional metadata, etc.

        Args:
            documents: List of Document objects from chunk().

        Returns:
            Processed Document objects.
        """
        return documents

    @classmethod
    def _build_default_config(cls) -> TransformConfig:
        """Build default config from Config."""
        from src.shared.config import get_config

        cfg = get_config()
        return TransformConfig(
            collection_name=getattr(cfg, "qdrant_collection_name", "default"),
            model_name=getattr(cfg, "embedding_model_name", "intfloat/multilingual-e5-small"),
            chunk_size=getattr(cfg, "chunk_size", 1024),
            chunk_overlap=getattr(cfg, "chunk_overlap", 100),
            enable_sbert=getattr(cfg, "enable_sbert", True),
            enable_rich_chunks=getattr(cfg, "enable_rich_chunks", False),
            enable_eval_questions=getattr(cfg, "enable_eval_questions", False),
        )

    @classmethod
    def can_handle(cls, file_path: Path | str) -> bool:
        """Check if this transform can handle the given file.

        Uses SUPPORTED_EXTENSIONS for format detection.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if this transform can handle the file.
        """
        path = Path(file_path)
        return path.suffix.lower() in cls.SUPPORTED_EXTENSIONS

    def run(self, file_path: Path) -> list[Document]:
        """Execute the full transform pipeline: parse -> chunk -> post_process.

        Args:
            file_path: Path to the source file.

        Returns:
            List of Document objects ready for embedding/indexing.
        """
        documents = self.parse(file_path)
        chunks = self.chunk(documents)
        return self.post_process(chunks)
