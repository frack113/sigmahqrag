"""Ingestion pipeline with LlamaIndex — config-driven, OpenVINO-accelerated."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import portalocker
from llama_index.core import VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import Document
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore

from src.back.embedding_config import EmbeddingTypeConfig

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_CHUNK_SIZE = 512
DEFAULT_CHUNK_OVERLAP = 50
DEFAULT_EMBED_BATCH_SIZE = 8
DEFAULT_NUM_WORKERS = 4
DEFAULT_SIMILARITY_TOP_K = 5
CACHE_DIR = Path("data/rag_cache")
LOCAL_EMBEDDINGS_DIR = Path("data/models/embeddings")

_pipeline_registry: dict[tuple[str, str], IngestionPipeline] = {}


def _first_configured_model(config: dict) -> str | None:
    for _type_key, type_config in config.items():
        if isinstance(type_config, dict) and "model" in type_config:
            return type_config["model"]
    return None


def build_embed_model(model_name: str) -> BaseEmbedding:
    local_path = LOCAL_EMBEDDINGS_DIR / model_name
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
        config_data = EmbeddingTypeConfig().load()
        self._model_name = model_name or _first_configured_model(config_data) or DEFAULT_MODEL
        self._collection_name = collection_name or "sigma_doc"
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

        if DEFAULT_CHUNK_SIZE <= 0:
            raise ValueError(f"chunk_size must be positive, got {DEFAULT_CHUNK_SIZE}")

        qdrant_healthy = self._check_qdrant_health()
        if qdrant_healthy:
            self._vector_store = self._get_qdrant_store()

        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        self._pipeline = IngestionPipeline(
            transformations=[
                SentenceSplitter(
                    chunk_size=DEFAULT_CHUNK_SIZE,
                    chunk_overlap=DEFAULT_CHUNK_OVERLAP,
                    include_metadata=True,
                ),
                self._embed_model,
            ],
            vector_store=self._vector_store,
            docstore=SimpleDocumentStore(),
        )

        cache_path = CACHE_DIR / self._collection_name
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
            cache_path = CACHE_DIR / self._collection_name
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

        return nodes

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
            cache_path = CACHE_DIR / self._collection_name
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

        return nodes

    def as_query_engine(
        self,
        similarity_top_k: int = DEFAULT_SIMILARITY_TOP_K,
    ):
        self.build()
        vector_store = self._vector_store

        if vector_store is None:
            from llama_index.core.vector_stores import SimpleVectorStore

            vector_store = SimpleVectorStore()
            logger.warning("Qdrant unavailable, using in-memory vector store")

        try:
            index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        except Exception as e:
            logger.warning("Failed to build index from vector store: %s", e)
            from llama_index.core.vector_stores import SimpleVectorStore

            vector_store = SimpleVectorStore()
            index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
        return index.as_query_engine(similarity_top_k=similarity_top_k)


def get_pipeline(
    model_name: str | None = None,
    collection_name: str | None = None,
) -> IngestionPipeline:
    """Get or create a cached IngestionPipeline keyed by (model, collection)."""
    config_data = EmbeddingTypeConfig().load()
    model = model_name or _first_configured_model(config_data) or DEFAULT_MODEL
    collection = collection_name or "sigma_doc"
    key = (model, collection)
    if key not in _pipeline_registry:
        builder = IngestionPipelineBuilder(
            model_name=model,
            collection_name=collection,
        )
        _pipeline_registry[key] = builder.build()
    return _pipeline_registry[key]
