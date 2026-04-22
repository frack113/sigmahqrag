"""Configuration module for shared paths and settings."""

from __future__ import annotations

import json
from pathlib import Path

LLAMA_PORT = 8080
QDRANT_PORT = 6333

LLAMA_HEALTH_ENDPOINT = "/v1/models"
QDRANT_HEALTH_ENDPOINT = "/health"

BIN_DIR = Path("bin")
LLAMA_BIN_PATH = BIN_DIR / "llama-server"
QDRANT_BIN_PATH = BIN_DIR / "qdrant"

MODELS_DIR = Path("models")
LLM_DIR = MODELS_DIR / "llm"
EMBEDDINGS_DIR = MODELS_DIR / "embeddings"

LOGS_DIR = Path("logs")
DATA_DIR = Path("data")
QDRANT_STORAGE_DIR = Path("qdrant/storage")

CONFIG_FILE = Path("config.json")


def load_config() -> dict:
    """Load configuration from file."""
    if CONFIG_FILE.exists():
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def save_config(config: dict) -> None:
    """Save configuration to file."""
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def get_backend() -> str:
    """Get llama.cpp backend (cpu, cuda, hip, vulkan)."""
    return load_config().get("backend", "cpu")


def set_backend(backend: str) -> None:
    """Set llama.cpp backend."""
    config = load_config()
    config["backend"] = backend
    save_config(config)