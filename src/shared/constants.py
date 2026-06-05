"""Shared constants - single source of truth for cross-cutting values."""

# Schema version for DuckDB database
# Increment when schema changes (initdb.sql modifications)
SCHEMA_VERSION = 1

# Sigma specification repository
SIGMA_SPEC_REPO = "https://github.com/SigmaHQ/sigma-specification"
# Pin to specific tag for reproducibility and security
SIGMA_SPEC_REF = "main"

# Default configuration values (used by init_projet.py DEFAULT_TOML generation)
DEFAULT_LLAMA_BASE_URL = "http://127.0.0.1:8080"
DEFAULT_QDRANT_BASE_URL = "http://127.0.0.1:6333"
DEFAULT_QDRANT_COLLECTION = "sigma_docs"
DEFAULT_QDRANT_VECTOR_SIZE = 384
DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"
