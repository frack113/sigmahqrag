"""Central configuration module — DuckDB (backend, logging) + defaults."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


BASE_DIR = Path("data").resolve()
BIN_DIR = BASE_DIR / "bin"
MODELS_DIR = BASE_DIR / "models"
LLM_DIR = MODELS_DIR / "llm"
EMBEDDINGS_DIR = MODELS_DIR / "embeddings"
LOGS_DIR = BASE_DIR / "logs"
PID_DIR = BASE_DIR / "pids"
TEMP_DIR = BASE_DIR / "temp"


@dataclass
class Config:
    gpu_type: str = "cpu"
    os: str = "windows"
    llamacpp_version: str = "0"
    qdrant_version: str = "0"
    qdrant_webui_version: str = "0"

    llm_dir: str = "data/models/llm"
    embeddings_dir: str = "data/models/embeddings"

    llama_base_url: str = "http://127.0.0.1:8080"
    llama_manage_internally: bool = True
    llama_model_name: str | None = None
    llama_binary_path: str = "data/bin/llamacpp"

    qdrant_base_url: str = "http://127.0.0.1:6333"
    qdrant_host: str = "127.0.0.1"
    qdrant_port: int = 6333
    qdrant_manage_internally: bool = True
    qdrant_collection_name: str = "sigma_docs"
    qdrant_vector_size: int = 384
    qdrant_binary_path: str = "data/bin/qdrant"
    qdrant_storage_path: str = "data/qdrant_storage/database"
    qdrant_snapshots_path: str = "data/qdrant_storage/snapshots"

    paths_logs_dir: str = "data/logs"
    paths_temp_dir: str = "data/temp"
    paths_duckdb_path: str = "data/duckdb/sigmahq.duckdb"
    paths_github_dir: str = "data/github"
    paths_rag_cache_dir: str = "data/rag_cache"
    paths_model_registry: str = "data/models/registry.json"
    paths_sigma_ref_docs_dir: str = "data/documents/sigmaref"
    paths_spec_repos_dir: str = "data/specification"
    paths_sigma_spec_dir: str = "data/specification/sigmahq/sigma-specification"

    local_documents_path: str = "data/documents/local"
    sigmaref_documents_path: str = "data/documents/sigmaref"

    logging_level: str = "INFO"
    logging_log_max_size: str = "10M"
    logging_log_max_file: int = 5
    logging_clean_at_startup: bool = False

    def __post_init__(self) -> None:
        pass

    def to_dict(self) -> dict[str, Any]:
        return {
            "services": {
                "llama": {
                    "base_url": self.llama_base_url,
                    "manage_internally": self.llama_manage_internally,
                },
                "qdrant": {
                    "base_url": self.qdrant_base_url,
                    "manage_internally": self.qdrant_manage_internally,
                },
            },
            "Hardware": {
                "os": self.os,
                "gpu": self.gpu_type,
            },
            "logging": {
                "level": self.logging_level,
                "log_max_size": self.logging_log_max_size,
                "log_max_file": self.logging_log_max_file,
                "clean_at_startup": self.logging_clean_at_startup,
            },
        }

    def save(self) -> bool:
        """Persist config — no-op since shared must not depend on back."""
        return True

    @classmethod
    def init_app(cls) -> Config:
        global _config
        cls.ensure_qdrant_config()
        cfg = cls()
        _config = cfg
        return cfg

    def resolve_llamacpp_bin_path(self) -> Path:
        """Resolve llama binary path with fallback to old location."""
        path = Path(self.llama_binary_path).resolve()
        if path.exists():
            return path
        old_path = Path("data/bin/llamacpp").resolve()
        if old_path.exists():
            logger.warning(
                "Using old llama binary path %s; update config services.llama.binary_path",
                old_path,
            )
            return old_path
        return path

    @staticmethod
    def ensure_qdrant_config() -> None:
        """Generate qdrant config.yaml if not exists."""
        qdrant_dir = Path(Config().qdrant_binary_path).resolve()
        config_file = qdrant_dir / "config" / "config.yaml"

        if config_file.exists():
            return

        try:
            template_path = Path("templates/qdrant/config.yaml.j2")
            if template_path.exists():
                import jinja2

                template = jinja2.Template(template_path.read_text(), autoescape=True)
                config = Config()
                storage_path = Path(config.qdrant_storage_path).resolve().as_posix()
                snapshots_path = Path(config.qdrant_snapshots_path).resolve().as_posix()
                rendered = template.render(
                    storage_path=storage_path,
                    snapshots_path=snapshots_path,
                )
                config_file.parent.mkdir(parents=True, exist_ok=True)
                config_file.write_text(rendered)
                logger.info(f"Generated Qdrant config at {config_file}")
        except Exception as e:
            logger.warning(f"Could not generate Qdrant config: {e}")


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config.init_app()
    return _config
