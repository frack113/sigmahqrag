"""Central configuration module using data/sigmahqrag.toml."""

from __future__ import annotations

import logging
import platform
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

BASE_DIR = Path("data")
BIN_DIR = BASE_DIR / "bin"
MODELS_DIR = BASE_DIR / "models"
LLM_DIR = MODELS_DIR / "llm"
EMBEDDINGS_DIR = MODELS_DIR / "embeddings"
LOGS_DIR = BASE_DIR / "logs"

LLAMA_BIN_PATH = BIN_DIR / "llama-cpp"
QDRANT_BIN_PATH = BIN_DIR / "qdrant"
QDRANT_STORAGE_DIR = BASE_DIR / "qdrant_storage"
DATA_DIR = BASE_DIR

DEFAULT_CONFIG = {
    "backend": {
        "gpu_type": "cpu",
        "os": None,
        "llamacpp_version": None,
        "qdrant_version": None,
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
        "logs_dir": "data/logs",
    },
    "logging": {
        "level": "INFO",
    },
}

CONFIG_FILE = Path("data/sigmahqrag.toml")

_toml_service = None


def _get_toml_service():
    """Get or create the TOML service singleton."""
    global _toml_service
    if _toml_service is None:
        from src.shared.toml_service import TOMLService

        _toml_service = TOMLService(CONFIG_FILE)
    return _toml_service


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    """Load configuration from TOML file with defaults.
    
    Returns:
        Dict with configuration (merged with defaults)
    """
    ensure_qdrant_config()
    config = DEFAULT_CONFIG.copy()
    toml_service = _get_toml_service()
    file_config = toml_service.load()
    
    if file_config:
        from src.shared import deep_merge
        deep_merge(config, file_config)
        logger.info(f"Loaded config from {CONFIG_FILE}")
    
    return config


def get_backend_gpu_type() -> str:
    """Get GPU type from config (hip, cuda, cpu)."""
    return load_config().get("backend", {}).get("gpu_type", "cpu")


def get_backend_os() -> str:
    """Get OS from config (windows, linux, macos)."""
    return load_config().get("backend", {}).get("os", "windows")


def set_backend_gpu_type(gpu_type: str) -> None:
    """Set GPU type in config and persist to TOML."""
    config = load_config()
    if "backend" not in config:
        config["backend"] = {}
    config["backend"]["gpu_type"] = gpu_type
    _persist_config(config)

def set_backend_os_type(os_type: str) -> None:
    """Set OS type in config and persist to TOML."""
    config = load_config()
    if "backend" not in config:
        config["backend"] = {}
    config["backend"]["os"] = os_type
    _persist_config(config)


def get_llamacpp_version() -> str | None:
    """Get installed llama.cpp version from config."""
    return load_config().get("backend", {}).get("llamacpp_version")


def set_llamacpp_version(version: str) -> None:
    """Set llama.cpp version in config."""
    config = load_config()
    if "backend" not in config:
        config["backend"] = {}
    config["backend"]["llamacpp_version"] = version
    _persist_config(config)


def get_qdrant_version() -> str | None:
    """Get installed qdrant version from config."""
    return load_config().get("backend", {}).get("qdrant_version")


def set_qdrant_version(version: str) -> None:
    """Set qdrant version in config."""
    config = load_config()
    if "backend" not in config:
        config["backend"] = {}
    config["backend"]["qdrant_version"] = version
    _persist_config(config)


def _persist_config(config: dict[str, Any]) -> None:
    """Persist the updated configuration to the TOML file."""
    toml_service = _get_toml_service()
    toml_service.save(config)


def ensure_qdrant_config() -> None:
    """Ensure qdrant.yaml exists and is updated based on sigmahqrag.toml."""
    try:
        # We use _get_toml_service().load() to avoid recursion with load_config()
        toml_service = _get_toml_service()
        file_config = toml_service.load() or {}
        
        # Get qdrant config from loaded file, or use defaults if not present
        qdrant_cfg = file_config.get("services", {}).get("qdrant", {})
        if not qdrant_cfg and "services" in DEFAULT_CONFIG:
             qdrant_cfg = DEFAULT_CONFIG["services"].get("qdrant", {})

        host = qdrant_cfg.get("host", "127.0.0.1")
        port = qdrant_cfg.get("port", 6333)
        
        # Use absolute path for storage location to avoid ambiguity
        storage_path = QDRANT_STORAGE_DIR.resolve().as_posix()
        
        yaml_content = f'storage:\n  location: "{storage_path}"\nservice:\n  host: "{host}"\n  port: {port}\n'
        
        config_path = Path("data/config/qdrant.yaml")
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(yaml_content)
    except Exception as e:
        logger.error(f"Failed to ensure qdrant.yaml: {e}")



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
