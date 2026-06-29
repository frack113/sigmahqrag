"""Sparse encoder for hybrid search — delegates to llama-index's default_sparse_encoder.

Uses transformers (PyTorch) via llama-index's built-in utility,
eliminating the fastembed dependency entirely.
"""

from __future__ import annotations

import logging

from llama_index.vector_stores.qdrant.utils import (
    SparseEncoderCallable,
    default_sparse_encoder,
)

from src.config.settings import SPARSE_MODEL_DIR

logger = logging.getLogger(__name__)


def create_sparse_encoder() -> SparseEncoderCallable:
    model_path = str(SPARSE_MODEL_DIR)
    if not SPARSE_MODEL_DIR.exists():
        raise FileNotFoundError(
            f"Sparse model not found at {SPARSE_MODEL_DIR}. "
            "Run 'uv run python scripts/download_sparse_model.py' to download it."
        )
    return default_sparse_encoder(model_path)
