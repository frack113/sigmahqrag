"""Application constants - single source of truth for cross-cutting values."""

SCHEMA_VERSION = 1

SIGMA_SPEC_REPO = "https://github.com/SigmaHQ/sigma-specification"
SIGMA_SPEC_REF = "main"

DEFAULT_LLAMA_BASE_URL = "http://127.0.0.1:8080"
DEFAULT_QDRANT_BASE_URL = "http://127.0.0.1:6333"
DEFAULT_QDRANT_COLLECTION = "sigma_docs"
DEFAULT_QDRANT_VECTOR_SIZE = 384
DEFAULT_EMBEDDING_MODEL = "intfloat/multilingual-e5-small"

# ── TOML configuration reference ──
# All valid TOML keys grouped by section. Used by _generate_custom_toml()
# to avoid silently dropping new config options from generated sigmarag.toml.

TOML_SECTIONS = frozenset(
    {
        "services.llama",
        "services.qdrant",
        "logging",
        "Hardware",
    }
)

TOML_CONFIG_KEYS: dict[str, list[str]] = {
    "services.llama": ["base_url", "manage_internally"],
    "services.qdrant": ["base_url", "manage_internally", "collection_name", "vector_size"],
    "logging": ["level", "log_max_size", "log_max_file", "clean_at_startup"],
    "Hardware": ["os", "gpu"],
}
