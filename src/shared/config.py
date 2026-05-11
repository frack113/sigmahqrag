"""Central configuration module using data/sigmahqrag.toml."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


BASE_DIR = Path("data").resolve()
CONFIG_FILE = BASE_DIR / "sigmahqrag.toml"
BIN_DIR = BASE_DIR / "bin"
MODELS_DIR = BASE_DIR / "models"
LLM_DIR = MODELS_DIR / "llm"
EMBEDDINGS_DIR = MODELS_DIR / "embeddings"
LOGS_DIR = BASE_DIR / "logs"
PID_DIR = BASE_DIR / "pids"
QDRANT_STORAGE_DIR = BASE_DIR / "qdrant_storage"
TEMP_DIR = BASE_DIR / "temp"
DATA_DIR = BASE_DIR


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
    llama_model_name: str | None = None
    llama_binary_path: str = "data/bin/llamacpp"

    qdrant_host: str = "127.0.0.1"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "sigma_rules"
    qdrant_vector_size: int = 384
    qdrant_binary_path: str = "data/bin/qdrant"
    qdrant_storage_path: str = "data/qdrant_storage/database"
    qdrant_snapshots_path: str = "data/qdrant_storage/snapshots"

    paths_bin_dir: str = "data/bin"
    paths_models_dir: str = "data/models"
    paths_logs_dir: str = "data/logs"
    paths_temp_dir: str = "data/temp"

    logging_level: str = "INFO"

    def __post_init__(self) -> None:
        self._load_from_toml()

    def _load_from_toml(self) -> None:
        if not CONFIG_FILE.exists():
            return
        try:
            from src.shared.toml_service import TOMLService

            toml_service = TOMLService(CONFIG_FILE)
            file_config = toml_service.load()
            if file_config:
                self._apply_nested_config(file_config)
                logger.info(f"Loaded config from {CONFIG_FILE}")
        except Exception as e:
            logger.warning(f"Failed to load config from {CONFIG_FILE}: {e}")

    def _apply_nested_config(self, nested: dict[str, Any]) -> None:
        """Apply nested config dict to dataclass fields."""
        if "backend" in nested:
            backend = nested["backend"]
            if "gpu_type" in backend:
                self.gpu_type = backend["gpu_type"]
            if "os" in backend:
                self.os = backend["os"]
            if "llamacpp_version" in backend:
                self.llamacpp_version = backend["llamacpp_version"]
            if "qdrant_version" in backend:
                self.qdrant_version = backend["qdrant_version"]
            if "qdrant_webui_version" in backend:
                self.qdrant_webui_version = backend["qdrant_webui_version"]

        if "models" in nested:
            models = nested["models"]
            if "llm_dir" in models:
                self.llm_dir = models["llm_dir"]
            if "embeddings_dir" in models:
                self.embeddings_dir = models["embeddings_dir"]

        if "services" in nested:
            services = nested["services"]
            if "llama" in services:
                llama = services["llama"]
                if "base_url" in llama:
                    self.llama_base_url = llama["base_url"]
                if "model_name" in llama:
                    self.llama_model_name = llama["model_name"]
                if "binary_path" in llama:
                    self.llama_binary_path = llama["binary_path"]
            if "qdrant" in services:
                qdrant = services["qdrant"]
                if "host" in qdrant:
                    self.qdrant_host = qdrant["host"]
                if "port" in qdrant:
                    self.qdrant_port = qdrant["port"]
                if "collection_name" in qdrant:
                    self.qdrant_collection_name = qdrant["collection_name"]
                if "vector_size" in qdrant:
                    self.qdrant_vector_size = qdrant["vector_size"]
                if "binary_path" in qdrant:
                    self.qdrant_binary_path = qdrant["binary_path"]
                if "storage_path" in qdrant:
                    self.qdrant_storage_path = qdrant["storage_path"]
                if "snapshots_path" in qdrant:
                    self.qdrant_snapshots_path = qdrant["snapshots_path"]

        if "paths" in nested:
            paths = nested["paths"]
            if "bin_dir" in paths:
                self.paths_bin_dir = paths["bin_dir"]
            if "models_dir" in paths:
                self.paths_models_dir = paths["models_dir"]
            if "logs_dir" in paths:
                self.paths_logs_dir = paths["logs_dir"]
            if "temp_dir" in paths:
                self.paths_temp_dir = paths["temp_dir"]

        if "logging" in nested:
            logging_cfg = nested["logging"]
            if "level" in logging_cfg:
                self.logging_level = logging_cfg["level"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "backend": {
                "gpu_type": self.gpu_type,
                "os": self.os,
                "llamacpp_version": self.llamacpp_version,
                "qdrant_version": self.qdrant_version,
                "qdrant_webui_version": self.qdrant_webui_version,
            },
            "models": {
                "llm_dir": self.llm_dir,
                "embeddings_dir": self.embeddings_dir,
            },
            "services": {
                "llama": {
                    "base_url": self.llama_base_url,
                    "model_name": self.llama_model_name,
                    "binary_path": self.llama_binary_path,
                },
                "qdrant": {
                    "host": self.qdrant_host,
                    "port": self.qdrant_port,
                    "collection_name": self.qdrant_collection_name,
                    "vector_size": self.qdrant_vector_size,
                    "binary_path": self.qdrant_binary_path,
                    "storage_path": self.qdrant_storage_path,
                    "snapshots_path": self.qdrant_snapshots_path,
                },
            },
            "paths": {
                "bin_dir": self.paths_bin_dir,
                "models_dir": self.paths_models_dir,
                "logs_dir": self.paths_logs_dir,
                "temp_dir": self.paths_temp_dir,
            },
            "logging": {
                "level": self.logging_level,
            },
        }

    def save(self) -> bool:
        try:
            from src.shared.toml_service import TOMLService

            toml_service = TOMLService(CONFIG_FILE)
            return toml_service.save(self.to_dict())
        except Exception as e:
            logger.error(f"Failed to save config to {CONFIG_FILE}: {e}")
            return False

    @classmethod
    def reload(cls) -> Config:
        return cls()

    @staticmethod
    def get_llamacpp_bin_path() -> Path:
        return Path(Config().llama_binary_path).resolve()

    @staticmethod
    def get_qdrant_bin_path() -> Path:
        return Path(Config().qdrant_binary_path).resolve()

    @staticmethod
    def ensure_data_folder() -> None:
        BASE_DIR.mkdir(parents=True, exist_ok=True)
        for subdir in (
            BIN_DIR,
            MODELS_DIR,
            LLM_DIR,
            EMBEDDINGS_DIR,
            LOGS_DIR,
            PID_DIR,
            QDRANT_STORAGE_DIR,
            TEMP_DIR,
        ):
            subdir.mkdir(parents=True, exist_ok=True)
        logger.info(f"Data folder ensured at {BASE_DIR}")

    @staticmethod
    def ensure_config_file() -> None:
        if not CONFIG_FILE.exists():
            default_config = Config()
            try:
                from src.shared.toml_service import TOMLService

                toml_service = TOMLService(CONFIG_FILE)
                toml_service.save(default_config.to_dict())
                logger.info(f"Created default config at {CONFIG_FILE}")
            except Exception as e:
                logger.error(f"Failed to create config: {e}")
        else:
            config = Config()
            config.save()
            logger.info(f"Updated config at {CONFIG_FILE}")

    @staticmethod
    def ensure_qdrant_config() -> None:
        """Generate qdrant config.yaml if not exists."""
        qdrant_dir = Path(Config().qdrant_binary_path).resolve()
        config_file = qdrant_dir / "config" / "config.yaml"

        if config_file.exists():
            return

        try:
            template_path = Path("templates/config.yaml.j2")
            if template_path.exists():
                import jinja2

                template = jinja2.Template(template_path.read_text())
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

    @staticmethod
    def init_app() -> Config:
        Config.ensure_data_folder()
        Config.ensure_config_file()
        Config.ensure_qdrant_config()
        return Config()


_config: Config | None = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()
    return _config
