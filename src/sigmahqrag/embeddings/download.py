"""Embedding model management."""

import logging
from pathlib import Path

from ..utils import download_file

logger = logging.getLogger(__name__)

DEFAULT_EMBEDDINGS_DIR = Path("models/embeddings")


def get_embedding_model_path(model_name: str, embeddings_dir: Path | None = None) -> Path:
    """Get path to an embedding model file.

    Args:
        model_name: Name of the model file
        embeddings_dir: Embeddings directory (default: models/embeddings/)

    Returns:
        Path to the model
    """
    if embeddings_dir is None:
        embeddings_dir = DEFAULT_EMBEDDINGS_DIR

    return embeddings_dir / model_name


def is_embedding_model_downloaded(model_name: str, embeddings_dir: Path | None = None) -> bool:
    """Check if embedding model is already downloaded.

    Args:
        model_name: Name of the model
        embeddings_dir: Embeddings directory (default: models/embeddings/)

    Returns:
        True if model exists
    """
    model_path = get_embedding_model_path(model_name, embeddings_dir)
    return model_path.exists()


def download_embedding_model(
    model_name: str,
    model_url: str,
    embeddings_dir: Path | None = None,
    force: bool = False,
) -> Path:
    """Download embedding model from URL.

    Args:
        model_name: Name for the downloaded file
        model_url: Direct URL to the GGUF file
        embeddings_dir: Directory to save model (default: models/embeddings/)
        force: Force re-download even if exists

    Returns:
        Path to downloaded model
    """
    import urllib.error
    import urllib.request

    if embeddings_dir is None:
        embeddings_dir = DEFAULT_EMBEDDINGS_DIR

    if not embeddings_dir.exists():
        embeddings_dir.mkdir(parents=True)

    model_path = get_embedding_model_path(model_name, embeddings_dir)

    if model_path.exists() and not force:
        logger.info(f"Embedding model already exists at {model_path}")
        return model_path

    logger.info(f"Downloading embedding model from {model_url}")

    try:
        download_file(model_url, model_path)
    except OSError as e:
        raise OSError(f"Failed to download embedding model: {e}") from e

    if not model_path.exists():
        raise OSError("Download completed but file not found")

    file_size = model_path.stat().st_size
    if file_size < 1024 * 100:
        model_path.unlink()
        raise OSError(f"Downloaded file too small ({file_size} bytes) - likely invalid")

    logger.info(
        f"Embedding model downloaded to {model_path} ({file_size / 1024 / 1024:.1f} MB)"
    )
    return model_path


def get_recommended_embedding_models() -> list[dict[str, str]]:
    """Get recommended embedding models for this project.

    Returns:
        List of recommended model info
    """
    return [
        {
            "name": "bge-small-en-v1.5-q4_0.gguf",
            "size": "130MB",
            "description": "BGE small English v1.5 Q4 - fast, good quality",
        },
        {
            "name": "bge-small-zh-v1.5-q4_0.gguf",
            "size": "130MB",
            "description": "BGE small Chinese v1.5 Q4",
        },
        {
            "name": "bge-multilingual-reranker-v1-m2.q4_0.gguf",
            "size": "560MB",
            "description": "BGE reranker - for better search",
        },
    ]
