"""Download LLM models from HuggingFace."""

import logging
import subprocess
from pathlib import Path


logger = logging.getLogger(__name__)

DEFAULT_MODELS_DIR = Path("models/llm")


def get_model_path(model_name: str, models_dir: Path | None = None) -> Path:
    """Get path to a model file.

    Args:
        model_name: Name of the model file
        models_dir: Models directory (default: models/llm/)

    Returns:
        Path to the model
    """
    if models_dir is None:
        models_dir = DEFAULT_MODELS_DIR

    return models_dir / model_name


def is_model_downloaded(model_name: str, models_dir: Path | None = None) -> bool:
    """Check if model is already downloaded.

    Args:
        model_name: Name of the model
        models_dir: Models directory (default: models/llm/)

    Returns:
        True if model exists
    """
    model_path = get_model_path(model_name, models_dir)
    return model_path.exists()


def download_model(
    model_name: str,
    model_url: str,
    models_dir: Path | None = None,
    force: bool = False,
) -> Path:
    """Download GGUF model from URL.

    Args:
        model_name: Name for the downloaded file
        model_url: Direct URL to the GGUF file
        models_dir: Directory to save model (default: models/llm/)
        force: Force re-download even if exists

    Returns:
        Path to downloaded model

    Raises:
        FileNotFoundError: If URL is invalid
        OSError: If download fails
    """
    import urllib.error
    import urllib.request

    if models_dir is None:
        models_dir = DEFAULT_MODELS_DIR

    if not models_dir.exists():
        models_dir.mkdir(parents=True)

    model_path = get_model_path(model_name, models_dir)

    if model_path.exists() and not force:
        logger.info(f"Model already exists at {model_path}")
        return model_path

    logger.info(f"Downloading model from {model_url}")

    try:
        with urllib.request.urlopen(model_url, timeout=600) as response:
            with open(model_path, "wb") as out_file:
                out_file.write(response.read())
    except urllib.error.URLError as e:
        raise OSError(f"Failed to download model: {e}") from e
    except IOError as e:
        if model_path.exists():
            model_path.unlink()
        raise OSError(f"Download failed: {e}") from e

    if not model_path.exists():
        raise OSError("Download completed but file not found")

    file_size = model_path.stat().st_size
    if file_size < 1024 * 1024:
        model_path.unlink()
        raise OSError(f"Downloaded file too small ({file_size} bytes) - likely invalid")

    logger.info(f"Model downloaded to {model_path} ({file_size / 1024 / 1024:.1f} MB)")
    return model_path


def search_models(query: str = "") -> list[dict[str, str]]:
    """Search for GGUF models on HuggingFace.

    Args:
        query: Search query

    Returns:
        List of model info dicts
    """
    logger.info(f"Searching HuggingFace for: {query}")
    return []


def get_recommended_models() -> list[dict[str, str]]:
    """Get recommended GGUF models for this project.

    Returns:
        List of recommended model info
    """
    return [
        {
            "name": "llama-3.1-8b-q4_0.gguf",
            "size": "4.9GB",
            "description": "Llama 3.1 8B Q4_0 - good balance",
        },
        {
            "name": "llama-3.1-8b-q8_0.gguf",
            "size": "8.9GB",
            "description": "Llama 3.1 8B Q8_0 - higher quality",
        },
        {
            "name": "qwen2.5-3b-instruct-q4_0.gguf",
            "size": "2.5GB",
            "description": "Qwen 2.5 3B - smaller, faster",
        },
    ]