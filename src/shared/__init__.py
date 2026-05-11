"""Shared utilities package."""

from src.shared.config import (
    BASE_DIR,
    BIN_DIR,
    DATA_DIR,
    DEFAULT_CONFIG,
    EMBEDDINGS_DIR,
    LLM_DIR,
    LOGS_DIR,
    MODELS_DIR,
    PID_DIR,
    QDRANT_STORAGE_DIR,
    get_backend_gpu_type,
    get_backend_os,
    get_llama_config,
    get_llamacpp_version,
    get_log_level,
    get_paths,
    get_qdrant_config,
    get_qdrant_version,
    load_config,
    set_backend_gpu_type,
    set_backend_os_type,
    set_llamacpp_version,
    set_qdrant_version,
)
from src.shared.config import (
    get_llamacpp_bin_path as LLAMA_BIN_PATH,  # noqa: N812
)
from src.shared.config import (
    get_qdrant_bin_path as QDRANT_BIN_PATH,  # noqa: N812
)
from src.shared.toml_service import TOMLService as TOMLService
from src.shared.toml_service import deep_merge as deep_merge

__all__ = [
    "TOMLService",
    "deep_merge",
    "BASE_DIR",
    "BIN_DIR",
    "DATA_DIR",
    "DEFAULT_CONFIG",
    "EMBEDDINGS_DIR",
    "LLAMA_BIN_PATH",
    "LLM_DIR",
    "LOGS_DIR",
    "MODELS_DIR",
    "PID_DIR",
    "QDRANT_BIN_PATH",
    "QDRANT_STORAGE_DIR",
    "get_backend_gpu_type",
    "get_backend_os",
    "get_llama_config",
    "get_llamacpp_version",
    "get_log_level",
    "get_paths",
    "get_qdrant_config",
    "get_qdrant_version",
    "load_config",
    "set_backend_gpu_type",
    "set_llamacpp_version",
    "set_backend_os_type",
    "set_qdrant_version",
]
