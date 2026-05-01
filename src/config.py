"""Central configuration module using data/sigmahqrag.toml."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BASE_DIR = Path("data")
BIN_DIR = BASE_DIR / "bin"
MODELS_DIR = BASE_DIR / "models"
LLM_DIR = MODELS_DIR / "llm"
EMBEDDINGS_DIR = MODELS_DIR / "embeddings"
LOGS_DIR = Path("logs")
BACKUP_DIR = Path("backups")
MAX_BACKUPS = 5
LLAMA_BIN_PATH = BIN_DIR / "llama.cpp"
QDRANT_BIN_PATH = BIN_DIR / "qdrant"
QDRANT_STORAGE_DIR = BASE_DIR / "qdrant_storage"
DATA_DIR = BASE_DIR

# Default configuration
DEFAULT_CONFIG = {
    "backend": {
        "gpu_type": "cpu",  # hip, cuda, cpu
    },
    "models": {
        "llm_dir": "data/models/llm",
        "embeddings_dir": "data/models/embeddings",
    },
    "services": {
        "llama": {
            "base_url": "http://127.0.0.1:8080",
            "model_name": None,
        },
        "qdrant": {
            "host": "127.0.0.1",
            "port": 6333,
            "collection_name": "sigma_rules",
            "vector_size": 384,
        },
    },
    "paths": {
        "bin_dir": "data/bin",
        "models_dir": "data/models",
        "logs_dir": "logs",
        "backup_dir": "backups",
    },
    "logging": {
        "level": "INFO",  # DEBUG, INFO, WARNING, ERROR
    },
}

CONFIG_FILE = Path("data/sigmahqrag.toml")

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    """Load configuration from TOML file with defaults.

    Returns:
        Dict with configuration (merged with defaults)
    """
    config = DEFAULT_CONFIG.copy()

    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "rb") as f:
                file_config = tomllib.load(f)
                # Deep merge with defaults
                _deep_merge(config, file_config)
                logger.info(f"Loaded config from {CONFIG_FILE}")
        except Exception as e:
            logger.warning(f"Failed to load config from {CONFIG_FILE}: {e}")
    else:
        logger.info(f"Config file {CONFIG_FILE} not found, using defaults")

    return config


def _deep_merge(base: dict, override: dict) -> None:
    """Deep merge override into base (modifies base in place)."""
    for key, value in override.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def get_backend_gpu_type() -> str:
    """Get GPU type from config (hip, cuda, cpu)."""
    return load_config().get("backend", {}).get("gpu_type", "cpu")


def set_backend_gpu_type(gpu_type: str) -> None:
    """Set GPU type in config (only in memory for this session)."""
    config = load_config()
    if "backend" not in config:
        config["backend"] = {}
    config["backend"]["gpu_type"] = gpu_type


def get_llama_config() -> dict[str, Any]:
    """Get llama.cpp service configuration."""
    config = load_config()
    return config.get("services", {}).get("llama", {})


def get_qdrant_config() -> dict[str, Any]:
    """Get Qdrant service configuration."""
    config = load_config()
    return config.get("services", {}).get("qdrant", {})


def get_paths() -> dict[str, str]:
    """Get path configuration."""
    config = load_config()
    return config.get("paths", {})


def get_log_level() -> str:
    """Get logging level."""
    return load_config().get("logging", {}).get("level", "INFO")
