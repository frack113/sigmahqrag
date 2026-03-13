"""
Configuration Manager - Optimized for Gradio Native Integration

Uses simple, native methods without custom async wrappers:
- Direct JSON file operations
- Environment variable support
- Validation helpers
"""

import json
from pathlib import Path
from typing import Any

# Default configuration values
DEFAULT_CONFIG = {
    "server": {
        "host": "0.0.0.0",
        "port": 8002,
    },
    "rag": {
        "embedding_model": "all-MiniLM-L6-v2",
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "history_limit": 10,
    },
}


def create_config_manager(config_path: str | None = None) -> "ConfigManager":
    """Create a configured ConfigManager instance."""
    return ConfigManager(config_path)


class ConfigManager:
    """
    Configuration manager using simple JSON operations.

    Features:
    - Direct file-based config storage
    - Environment variable support for server settings
    - Validation helpers for click handlers
    """

    def __init__(self, config_path: str | None = None):
        self.config_dir = Path("data")
        self.config_file = config_path or (self.config_dir / "config.json")
        self._config: dict[str, Any] = {}

    def initialize(self) -> None:
        """Initialize the configuration manager with defaults if needed."""
        if not self.config_file.exists():
            self._config = DEFAULT_CONFIG.copy()

            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            self.save_config()

    def load_config(self, config_path: str | None = None) -> bool:
        """Load configuration from file."""
        if config_path:
            path = Path(config_path)
        else:
            path = self.config_file

        try:
            with open(path, encoding="utf-8") as f:
                self._config = json.load(f)
            return True
        except Exception as e:
            print(f"Error loading config: {e}")
            return False

    def save_config(self, path: str | Path | None = None) -> bool:
        """Save configuration to file."""
        if path:
            filepath = Path(path)
        else:
            filepath = self.config_file

        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2)

            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get_config(self) -> dict[str, Any]:
        """Get current configuration."""
        return self._config.copy()

    def merge_with_defaults(self) -> None:
        """Merge loaded config with defaults for missing keys."""
        defaults = DEFAULT_CONFIG.copy()

        for key, value in defaults.items():
            if key not in self._config:
                self._config[key] = value
            elif isinstance(value, dict):
                self._config[key] = {
                    **value,
                    **self._config[key],
                }

    def validate_config(self) -> bool:
        """Validate configuration values."""
        errors = []

        # Server validation
        if "server" not in self._config:
            errors.append("Missing 'server' section")
        else:
            server = self._config["server"]

            if (
                not isinstance(server.get("port"), int)
                or server["port"] < 1024
                or server["port"] > 65535
            ):
                errors.append(f"Invalid port: {server.get('port')}")

            if "host" in server and not server["host"].startswith(
                ("http://", "https://", "0.", "1.")
            ):
                errors.append(f"Invalid host: {server.get('host')}")

        # RAG validation
        if "rag" not in self._config:
            errors.append("Missing 'rag' section")
        else:
            rag = self._config["rag"]

            if not isinstance(rag.get("chunk_size"), int) or rag["chunk_size"] <= 0:
                errors.append(f"Invalid chunk_size: {rag.get('chunk_size')}")

            if (
                not isinstance(rag.get("chunk_overlap"), int)
                or rag["chunk_overlap"] < 0
            ):
                errors.append(f"Invalid chunk_overlap: {rag.get('chunk_overlap')}")

        return len(errors) == 0

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        keys = key.split(".")

        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value by key."""
        keys = key.split(".")[:-1]
        last_key = key.split(".")[-1]

        if not keys:
            self._config[last_key] = value
        else:
            parent = self._config
            for k in keys:
                if k not in parent:
                    parent[k] = {}
                parent = parent[k]

            parent[last_key] = value

    def update_server_config(
        self, host: str | None = None, port: int | None = None
    ) -> None:
        """Update server configuration."""
        if "server" not in self._config:
            self._config["server"] = {}

        if host is not None:
            self._config["server"]["host"] = host

        if port is not None:
            self._config["server"]["port"] = port

    def update_rag_config(
        self,
        embedding_model: str | None = None,
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        history_limit: int | None = None,
    ) -> None:
        """Update RAG configuration."""
        if "rag" not in self._config:
            self._config["rag"] = {}

        if embedding_model is not None:
            self._config["rag"]["embedding_model"] = embedding_model

        if chunk_size is not None:
            self._config["rag"]["chunk_size"] = chunk_size

        if chunk_overlap is not None:
            self._config["rag"]["chunk_overlap"] = chunk_overlap

        if history_limit is not None:
            self._config["rag"]["history_limit"] = history_limit

    def get_validated_value(
        self,
        min_val: float | int | None = None,
        max_val: float | int | None = None,
        allow_empty: bool = False,
    ) -> str:
        """Get validated string value for Gradio UI."""
        if allow_empty and not self._config.get("server", {}).get("api_key"):
            return ""  # Allow empty for API key fields

        if min_val is not None and max_val is not None:
            val = self._config.get("rag", {}).get("chunk_size", 1000)

            if isinstance(val, str):
                try:
                    val = int(val)
                except ValueError:
                    val = min_val

            val = float(min(max_val if max_val else val, min_val))
            return str(int(val))

        return str(self._config.get("server", {}).get("host", "0.0.0.0"))
