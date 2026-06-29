"""Ingestion pipeline with LlamaIndex — config-driven, OpenVINO-accelerated."""

from __future__ import annotations

import os

os.environ.setdefault("DISABLE_SAFETENSORS_CONVERSION", "1")
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import logging
import threading
from pathlib import Path
from typing import Any

import portalocker
from llama_index.core import VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import MarkdownNodeParser, SentenceSplitter
from llama_index.core.schema import Document
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore

from src.config.settings import get_config

logger = logging.getLogger(__name__)

_embed_model: Any | None = None
_embed_model_lock = threading.Lock()

DEFAULT_MODEL = "intfloat/multilingual-e5-small"
DEFAULT_CHUNK_SIZE = 1024
DEFAULT_CHUNK_OVERLAP = 100
DEFAULT_EMBED_BATCH_SIZE = 8
DEFAULT_NUM_WORKERS = 0
DEFAULT_SIMILARITY_TOP_K = 5

# Collection names that use the transform system instead of SentenceSplitter.
TRANSFORM_COLLECTIONS: set[str] = {"sigma_rules", "sigma_spec"}


# Chunkers optimized per source type
SOURCE_CHUNK_CONFIG: dict[str, dict[str, Any]] = {
    "sigma_docs": {
        "chunk_size": 1024,
        "chunk_overlap": 100,
        "use_markdown_parser": True,
    },
    "sigma_spec": {
        "chunk_size": 1024,
        "chunk_overlap": 100,
        "use_markdown_parser": True,
    },
    "github": {
        "chunk_size": 1024,
        "chunk_overlap": 100,
        "use_markdown_parser": True,
    },
    "local": {
        "chunk_size": 1024,
        "chunk_overlap": 100,
        "use_markdown_parser": True,
    },
    "sigma_rules": {
        "chunk_size": 512,
        "chunk_overlap": 50,
        "use_markdown_parser": False,
    },
}


def _get_chunker_for_collection(collection_name: str) -> tuple[Any, Any]:
    """Return (markdown_parser, sentence_splitter) for the given collection."""
    source = ""
    if collection_name:
        parts = collection_name.lower().split("/")
        source = parts[0] if parts else collection_name

    cfg = SOURCE_CHUNK_CONFIG.get(source, SOURCE_CHUNK_CONFIG["sigma_docs"])
    md_parser = MarkdownNodeParser(include_metadata=True) if cfg["use_markdown_parser"] else None
    splitter = SentenceSplitter(
        chunk_size=cfg["chunk_size"],
        chunk_overlap=cfg["chunk_overlap"],
        include_metadata=True,
    )
    return md_parser, splitter


_pipeline_registry: dict[tuple[str, str], IngestionPipeline] = {}
_embed_dim: int | None = None


def reset_pipeline_registry() -> None:
    """Clear all cached pipelines — call after changing the embedding model."""
    _pipeline_registry.clear()


def get_embedding_dimension() -> int:
    """Return the detected embedding dimension, or 384 as fallback."""
    return _embed_dim or 384


def _detect_embed_dim(model: BaseEmbedding) -> int:
    """Infer embedding dimension by encoding a short probe string."""
    try:
        vec = model.get_text_embedding("probe")
        return len(vec)
    except Exception:
        return 384


def build_embed_model(model_name: str) -> BaseEmbedding:
    local_path = Path(get_config().embeddings_dir) / model_name
    model_path = str(local_path) if local_path.exists() else model_name
    global _embed_dim

    try:
        logger.info("Loading embedding model from %s", model_path)
        # Air-gap mode: use only local files, no network calls to HF Hub
        import os as _os

        _was_offline = _os.environ.get("HF_HUB_OFFLINE") == "1"

        if not Path(model_path).exists():
            # Force offline mode when model is not found locally (air-gap)
            _os.environ["HF_HUB_OFFLINE"] = "1"

        # Suppress tqdm/progress bar output during model loading
        import sys as _sys
        from io import StringIO as _StringIO

        _old_stderr = _sys.stderr
        _sys.stderr = _StringIO()

        model = HuggingFaceEmbedding(
            model_name=model_path,
            device="cpu",
            embed_batch_size=DEFAULT_EMBED_BATCH_SIZE,
            query_instruction="query: ",
            text_instruction="passage: ",
        )

        # Restore stderr and previous offline state after loading
        _sys.stderr = _old_stderr
        if not _was_offline and "HF_HUB_OFFLINE" in _os.environ:
            del _os.environ["HF_HUB_OFFLINE"]

        _embed_dim = _detect_embed_dim(model)
        logger.info("Detected embedding dimension: %d", _embed_dim)
        return model
    except Exception as e:
        # Restore stderr on error too
        if " _sys" in dir() and hasattr(_sys, "stderr"):
            try:
                _sys.stderr = _old_stderr
            except:
                pass
        if not _was_offline and "HF_HUB_OFFLINE" in _os.environ:
            del _os.environ["HF_HUB_OFFLINE"]
        logger.error(
            "Embedding model %s failed to load (path: %s): %s",
            model_name,
            model_path,
            e,
        )
        raise


class IngestionPipelineBuilder:
    """Builds and manages a LlamaIndex IngestionPipeline with config-driven model selection."""

    _MODEL_NAME_TO_EMBED: dict[str, Any] = {}
    _MODEL_NAME_LOCK: threading.Lock = threading.Lock()

    def __init__(
        self,
        model_name: str | None = None,
        collection_name: str | None = None,
        num_workers: int = DEFAULT_NUM_WORKERS,
    ) -> None:
        if model_name is None:
            from src.infrastructure.database import DatabaseService

            model_name = DatabaseService.get_instance().get_active_embedding_model_name()
            self._model_name = model_name or DEFAULT_MODEL
        else:
            self._model_name = model_name
        self._collection_name = collection_name or "sigma_docs"
        self._num_workers = num_workers
        with self._MODEL_NAME_LOCK:
            if self._model_name not in self._MODEL_NAME_TO_EMBED:
                self._MODEL_NAME_TO_EMBED[self._model_name] = build_embed_model(self._model_name)
            self._embed_model = self._MODEL_NAME_TO_EMBED[self._model_name]
        self._pipeline: IngestionPipeline | None = None
        self._vector_store: QdrantVectorStore | None = None
        self._cached = False

    def _get_qdrant_store(self) -> QdrantVectorStore | None:
        try:
            from src.infrastructure.vectorstore.client import get_qdrant_client

            client = get_qdrant_client()
            return QdrantVectorStore(
                client=client,
                collection_name=self._collection_name,
                enable_hybrid=True,
                sparse_vector_name="text-sparse",
            )
        except Exception as e:
            logger.warning("Failed to connect to Qdrant: %s", e)
            return None

    def _check_qdrant_health(self) -> bool:
        try:
            from src.infrastructure.vectorstore.client import get_qdrant_client

            client = get_qdrant_client()
            client.get_collections()
            return True
        except Exception:
            return False

    def _get_transform(self) -> Any | None:
        """Detect and return a transform for the current collection.

        Returns:
            A DocumentTransform instance, or None if no transform matches.
        """
        source = ""
        if self._collection_name:
            parts = self._collection_name.lower().split("/")
            source = parts[0] if parts else self._collection_name

        from .. import TransformRegistry

        transform_cls = TransformRegistry.get(source)
        if transform_cls is None:
            return None

        from src.core.document.clients import get_llm_client

        from ..base import TransformConfig

        llm_client = get_llm_client()
        config = TransformConfig(
            collection_name=self._collection_name,
            collection=self._collection_name,
            model_name=self._model_name,
            chunk_size=SOURCE_CHUNK_CONFIG.get(source, {}).get("chunk_size", 512),
            chunk_overlap=SOURCE_CHUNK_CONFIG.get(source, {}).get("chunk_overlap", 50),
            llm_client=llm_client,
        )
        return transform_cls(config=config)

    def _uses_transform(self) -> bool:
        """Check if the current collection should use a transform."""
        source = ""
        if self._collection_name:
            parts = self._collection_name.lower().split("/")
            source = parts[0] if parts else self._collection_name
        return source in TRANSFORM_COLLECTIONS

    def build(
        self, skip_splitter: bool = False, skip_transform_transformations: bool = False
    ) -> IngestionPipeline:
        if self._pipeline is not None and self._cached:
            return self._pipeline

        qdrant_healthy = self._check_qdrant_health()
        if qdrant_healthy:
            self._vector_store = self._get_qdrant_store()

        cache_dir = Path(get_config().paths_rag_cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

        # For transform-based collections, skip SentenceSplitter — the transform
        # already produces appropriately-sized chunks.
        use_transform = not skip_transform_transformations and self._uses_transform()

        if use_transform or skip_splitter:
            md_parser = None
            splitter = None
            if skip_splitter:
                logger.debug("Skipping SentenceSplitter for collection '%s'", self._collection_name)
            if use_transform:
                logger.info(
                    "Using transform-based pipeline for collection '%s'", self._collection_name
                )
        else:
            md_parser, splitter = _get_chunker_for_collection(self._collection_name)

        transformations: list[Any] = [self._embed_model]

        if md_parser is not None:
            transformations.insert(0, md_parser)
        if splitter is not None:
            transformations.insert(0, splitter)

        self._pipeline = IngestionPipeline(
            transformations=transformations,
            vector_store=self._vector_store,
            docstore=SimpleDocumentStore(),
        )

        cache_path = cache_dir / self._collection_name
        lock_path = cache_path / "pipeline.lock"
        if cache_path.exists():
            try:
                with portalocker.Lock(
                    lock_path, timeout=5, flags=portalocker.LOCK_EX | portalocker.LOCK_NB
                ):
                    self._pipeline.load(str(cache_path))
                    logger.info("Restored pipeline cache from %s", cache_path)
            except portalocker.LockException:
                logger.warning("Cache lock acquisition failed, loading without lock")
                try:
                    self._pipeline.load(str(cache_path))
                except Exception as e:
                    logger.warning("Failed to restore pipeline cache: %s", e)
            except Exception as e:
                logger.warning("Failed to restore pipeline cache: %s", e)

        self._cached = qdrant_healthy
        return self._pipeline

    def run(
        self,
        documents: list[Document],
        num_workers: int | None = None,
        skip_splitter: bool = False,
    ) -> list[Any]:
        if not documents:
            return []

        # Filter documents with no text before embedding
        non_empty = [d for d in documents if (d.text or "").strip()]
        skipped = len(documents) - len(non_empty)
        if skipped:
            logger.warning("Filtered %d documents with empty text before embedding", skipped)
        if not non_empty:
            return []

        pipeline = self.build(skip_splitter=skip_splitter)
        nodes = pipeline.run(
            documents=non_empty,
            num_workers=num_workers or self._num_workers,
        )

        if self._cached:
            cache_dir = Path(get_config().paths_rag_cache_dir)
            cache_path = cache_dir / self._collection_name
            cache_path.mkdir(parents=True, exist_ok=True)
            lock_path = cache_path / "pipeline.lock"
            try:
                with portalocker.Lock(
                    lock_path, timeout=5, flags=portalocker.LOCK_EX | portalocker.LOCK_NB
                ):
                    pipeline.persist(str(cache_path))
            except portalocker.LockException:
                logger.warning("Cache lock acquisition failed, persisting without lock")
                try:
                    pipeline.persist(str(cache_path))
                except Exception as e:
                    logger.warning("Failed to persist pipeline cache: %s", e)
            except Exception as e:
                logger.warning("Failed to persist pipeline cache: %s", e)

        return list(nodes)

    def run_files(
        self,
        file_paths: list[str | Path],
        num_workers: int | None = None,
    ) -> list[Any]:
        """Run ingestion with automatic transform detection per file.

        For each file, detects a suitable DocumentTransform via the registry,
        runs the full transform pipeline (parse -> chunk -> post_process),
        then feeds the resulting Documents through the LlamaIndex pipeline.

        Args:
            file_paths: List of file paths to ingest.
            num_workers: Override number of workers for the pipeline.

        Returns:
            List of nodes produced by the pipeline.
        """
        from .. import TransformRegistry

        all_documents: list[Document] = []

        for file_path in file_paths:
            transform = TransformRegistry.find_for_file(file_path)
            if transform is not None:
                try:
                    transform_instance = transform(config=self._make_transform_config(file_path))
                    docs = transform_instance.run(Path(file_path))
                    all_documents.extend(docs)
                    logger.info(
                        "Transform %s produced %d document(s) from %s",
                        transform.__name__,
                        len(docs),
                        file_path,
                    )
                except Exception:
                    logger.exception("Transform %s failed for %s", transform.__name__, file_path)
                    continue
            else:
                logger.debug("No transform registered for file '%s', skipping", file_path)

        # Filter out documents with no text
        non_empty = [d for d in all_documents if (d.text or "").strip()]
        skipped = len(all_documents) - len(non_empty)
        if skipped:
            logger.warning("Filtered %d documents with empty text before embedding", skipped)
        all_documents = non_empty

        return self.run(all_documents, num_workers=num_workers)

    def _make_transform_config(self, file_path: str | Path) -> Any:
        """Build a TransformConfig suited for a specific file."""
        from src.core.document.clients import get_llm_client

        from ..base import TransformConfig

        source = ""
        if self._collection_name:
            parts = self._collection_name.lower().split("/")
            source = parts[0] if parts else self._collection_name

        chunk_cfg = SOURCE_CHUNK_CONFIG.get(source, {})

        return TransformConfig(
            collection_name=self._collection_name,
            collection=self._collection_name,
            model_name=self._model_name,
            chunk_size=chunk_cfg.get("chunk_size", 512),
            chunk_overlap=chunk_cfg.get("chunk_overlap", 50),
            llm_client=get_llm_client(),
        )

    async def arun(
        self,
        documents: list[Document],
        num_workers: int | None = None,
        skip_splitter: bool = False,
    ) -> list[Any]:
        if not documents:
            return []

        non_empty = [d for d in documents if (d.text or "").strip()]
        skipped = len(documents) - len(non_empty)
        if skipped:
            logger.warning("Filtered %d documents with empty text before embedding", skipped)
        if not non_empty:
            return []

        pipeline = self.build(skip_splitter=skip_splitter)
        nodes = await pipeline.arun(
            documents=non_empty,
            num_workers=num_workers or self._num_workers,
        )

        if self._cached:
            cache_dir = Path(get_config().paths_rag_cache_dir)
            cache_path = cache_dir / self._collection_name
            cache_path.mkdir(parents=True, exist_ok=True)
            lock_path = cache_path / "pipeline.lock"
            try:
                with portalocker.Lock(
                    lock_path, timeout=5, flags=portalocker.LOCK_EX | portalocker.LOCK_NB
                ):
                    pipeline.persist(str(cache_path))
            except portalocker.LockException:
                logger.warning("Cache lock acquisition failed, persisting without lock")
                try:
                    pipeline.persist(str(cache_path))
                except Exception as e:
                    logger.warning("Failed to persist pipeline cache: %s", e)
            except Exception as e:
                logger.warning("Failed to persist pipeline cache: %s", e)

        return list(nodes)

    def as_query_engine(
        self,
        similarity_top_k: int = DEFAULT_SIMILARITY_TOP_K,
    ):
        self.build()

        if self._vector_store is not None:
            try:
                index = VectorStoreIndex.from_vector_store(vector_store=self._vector_store)
                return index.as_query_engine(similarity_top_k=similarity_top_k)
            except Exception as e:
                logger.warning("Failed to build index from Qdrant vector store: %s", e)

        logger.warning(
            "Qdrant unavailable or failed, cannot serve queries — returning empty engine"
        )
        return None


def get_pipeline(
    model_name: str | None = None,
    collection_name: str | None = None,
) -> IngestionPipeline:
    """Get or create a cached IngestionPipeline keyed by (model, collection)."""
    if model_name is None:
        from src.infrastructure.database import DatabaseService

        model_name = (
            DatabaseService.get_instance().get_active_embedding_model_name() or DEFAULT_MODEL
        )
    model = model_name
    collection = collection_name or "sigma_docs"
    key = (model, collection)
    if key not in _pipeline_registry:
        builder = IngestionPipelineBuilder(
            model_name=model,
            collection_name=collection,
        )
        _pipeline_registry[key] = builder.build()
    return _pipeline_registry[key]
