"""Ingestion pipeline with LlamaIndex — config-driven, OpenVINO-accelerated."""

from __future__ import annotations

import logging
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

from src.shared.config import get_config

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_CHUNK_SIZE = 1024
DEFAULT_CHUNK_OVERLAP = 100
DEFAULT_EMBED_BATCH_SIZE = 8
DEFAULT_NUM_WORKERS = 4
DEFAULT_SIMILARITY_TOP_K = 5


# Chunkers optimized per source type
SOURCE_CHUNK_CONFIG: dict[str, dict[str, Any]] = {
    "sigmaref": {
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


def _get_chunker_for_collection(collection_name: str) -> tuple[Any, dict[str, Any]]:
    """Return (markdown_parser, sentence_splitter) for the given collection."""
    source = ""
    if collection_name:
        parts = collection_name.lower().split("/")
        source = parts[0] if parts else collection_name

    cfg = SOURCE_CHUNK_CONFIG.get(source, SOURCE_CHUNK_CONFIG["sigmaref"])
    md_parser = MarkdownNodeParser(include_metadata=True) if cfg["use_markdown_parser"] else None
    splitter = SentenceSplitter(
        chunk_size=cfg["chunk_size"],
        chunk_overlap=cfg["chunk_overlap"],
        include_metadata=True,
    )
    return md_parser, splitter


_pipeline_registry: dict[tuple[str, str], IngestionPipeline] = {}


def build_embed_model(model_name: str) -> BaseEmbedding:
    local_path = Path(get_config().embeddings_dir) / model_name
    model_path = str(local_path) if local_path.exists() else model_name
    try:
        logger.info("Loading embedding model from %s", model_path)
        return HuggingFaceEmbedding(
            model_name=model_path,
            device="cpu",
            embed_batch_size=DEFAULT_EMBED_BATCH_SIZE,
        )
    except Exception as e:
        logger.error(
            "Embedding model %s failed to load (path: %s): %s",
            model_name,
            model_path,
            e,
        )
        raise


class IngestionPipelineBuilder:
    """Builds and manages a LlamaIndex IngestionPipeline with config-driven model selection."""

    def __init__(
        self,
        model_name: str | None = None,
        collection_name: str | None = None,
        num_workers: int = DEFAULT_NUM_WORKERS,
    ) -> None:
        if model_name is None:
            from src.back.embedding_config import EmbeddingTypeConfig

            config_data = EmbeddingTypeConfig().load()
            self._model_name = (config_data.get("model") or "") or DEFAULT_MODEL
        else:
            self._model_name = model_name
        self._collection_name = collection_name or "sigmaref"
        self._num_workers = num_workers
        self._embed_model = build_embed_model(self._model_name)
        self._pipeline: IngestionPipeline | None = None
        self._vector_store: QdrantVectorStore | None = None
        self._cached = False

    def _get_qdrant_store(self) -> QdrantVectorStore | None:
        try:
            from src.back.qdrant.client import get_qdrant_client

            client = get_qdrant_client()
            return QdrantVectorStore(
                client=client,
                collection_name=self._collection_name,
            )
        except Exception as e:
            logger.warning("Failed to connect to Qdrant: %s", e)
            return None

    def _check_qdrant_health(self) -> bool:
        try:
            from src.back.qdrant.client import get_qdrant_client

            client = get_qdrant_client()
            client.get_collections()
            return True
        except Exception:
            return False

    def build(self) -> IngestionPipeline:
        if self._pipeline is not None and self._cached:
            return self._pipeline

        qdrant_healthy = self._check_qdrant_health()
        if qdrant_healthy:
            self._vector_store = self._get_qdrant_store()

        cache_dir = Path(get_config().paths_rag_cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

        md_parser, splitter = _get_chunker_for_collection(self._collection_name)

        transformations: list[Any] = [self._embed_model]

        if md_parser is not None:
            transformations.insert(0, md_parser)
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
                with portalocker.Lock(lock_path, timeout=5, flags=portalocker.LOCK_EX):
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
    ) -> list[Any]:
        if not documents:
            return []

        pipeline = self.build()
        nodes = pipeline.run(
            documents=documents,
            num_workers=num_workers or self._num_workers,
        )

        if self._cached:
            cache_dir = Path(get_config().paths_rag_cache_dir)
            cache_path = cache_dir / self._collection_name
            cache_path.mkdir(parents=True, exist_ok=True)
            lock_path = cache_path / "pipeline.lock"
            try:
                with portalocker.Lock(lock_path, timeout=5, flags=portalocker.LOCK_EX):
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

    async def arun(
        self,
        documents: list[Document],
        num_workers: int | None = None,
    ) -> list[Any]:
        if not documents:
            return []

        pipeline = self.build()
        nodes = await pipeline.arun(
            documents=documents,
            num_workers=num_workers or self._num_workers,
        )

        if self._cached:
            cache_dir = Path(get_config().paths_rag_cache_dir)
            cache_path = cache_dir / self._collection_name
            cache_path.mkdir(parents=True, exist_ok=True)
            lock_path = cache_path / "pipeline.lock"
            try:
                with portalocker.Lock(lock_path, timeout=5, flags=portalocker.LOCK_EX):
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

        if self._vector_store is None:
            from llama_index.core.vector_stores import SimpleVectorStore

            logger.warning("Qdrant unavailable, using in-memory vector store")
            vs: QdrantVectorStore | SimpleVectorStore = SimpleVectorStore()
        else:
            vs = self._vector_store

        try:
            index = VectorStoreIndex.from_vector_store(vector_store=vs)
        except Exception as e:
            logger.warning("Failed to build index from vector store: %s", e)
            from llama_index.core.vector_stores import SimpleVectorStore

            index = VectorStoreIndex.from_vector_store(vector_store=SimpleVectorStore())
        return index.as_query_engine(similarity_top_k=similarity_top_k)


def get_pipeline(
    model_name: str | None = None,
    collection_name: str | None = None,
) -> IngestionPipeline:
    """Get or create a cached IngestionPipeline keyed by (model, collection)."""
    if model_name is None:
        from src.back.embedding_config import EmbeddingTypeConfig

        config_data = EmbeddingTypeConfig().load()
        model_name = config_data.get("model") or DEFAULT_MODEL
    model = model_name
    collection = collection_name or "sigmaref"
    key = (model, collection)
    if key not in _pipeline_registry:
        builder = IngestionPipelineBuilder(
            model_name=model,
            collection_name=collection,
        )
        _pipeline_registry[key] = builder.build()
    return _pipeline_registry[key]
