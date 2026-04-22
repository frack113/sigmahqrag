"""Configuration module for shared paths and settings."""

from __future__ import annotations

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