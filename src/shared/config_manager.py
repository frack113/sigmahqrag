"""
Configuration Manager - Optimized for Gradio Native Integration with auto_reload support

Uses simple, native methods without custom async wrappers:
- Direct JSON file operations
- Environment variable support
- Validation helpers
- Supports auto_reload for Gradio application restart
"""

import json
import os
from pathlib import Path
from typing import Any

from src.application.application import MissingConfigError

# Configuration file path - must exist at startup
CONFIG_FILE_PATH = Path("data/config.json")


class ConfigManager:
    """
    Centralized Configuration Manager using simple JSON operations.

    Features:
    - Direct file-based config storage with auto_reload support for Gradio
    - Environment variable overrides (network.ip and network.port)
    - Validation helpers for CLI handlers
    - Thread-safe read/write operations
    - Auto-reload capability by setting GRADIO_AUTO_RELOAD env var
    """

    def __init__(self, config_path: str | None = None):
        """Initialize ConfigManager - config file must exist."""
        self.config_dir = Path("data")
        if config_path is None:
            raise ValueError("Config path is required - no defaults allowed")
        self.config_file = Path(config_path)
        self._config: dict[str, Any] = {}

    @property
    def auto_reload(self) -> bool:
        """Get auto_reload setting from network configuration."""
        return self._get_nested_value("network.auto_reload")

    @auto_reload.setter
    def auto_reload(self, value: bool):
        """Set auto_reload and trigger environment variable update."""
        self.set_nested("network.auto_reload", value)
        # Update GRADIO_AUTO_RELOAD environment variable if enabled
        os.environ["GRADIO_AUTO_RELOAD"] = str(value).lower()

    def initialize(self) -> None:
        """Validate that config file exists and is readable. Raises MissingConfigError if not found."""
        if not self.config_file.exists():
            raise MissingConfigError(
                f"Required configuration file must exist: {self.config_file}"
            )
        
        # Verify it's a valid JSON file
        try:
            with open(self.config_file, 'r') as f:
                json.load(f)
        except json.JSONDecodeError as e:
            raise MissingConfigError(
                f"Configuration file is not valid JSON: {self.config_file}\n{e}"
            ) from e

    def load_config(self) -> dict[str, Any]:
        """Load and parse configuration from JSON file."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = json.load(f)
            return self._config
        except FileNotFoundError:
            raise MissingConfigError(f"Configuration file not found: {self.config_file}")
        except json.JSONDecodeError as e:
            raise MissingConfigError(f"Invalid JSON in configuration file: {e}")


    def save_config(self, path: str | Path | None = None) -> bool:
        """Save configuration to file."""
        if path:
            filepath = Path(path)
        else:
            filepath = self.config_file

        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)

            # Ensure auto_reload is a boolean for proper environment variable handling
            if "network" in self._config and isinstance(self._config["network"], dict):
                auto_reload = self._config["network"].get("auto_reload")
                if auto_reload is not None:
                    self._config["network"]["auto_reload"] = bool(auto_reload)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2)

            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get_config(self) -> dict[str, Any]:
        """Get current configuration."""
        return self._config.copy()

    def validate_config(self) -> tuple[bool, list[str]]:
        """Validate configuration values. Returns (is_valid, errors)."""
        errors = []

        # Network validation
        if "network" not in self._config:
            errors.append("Missing 'network' section")
        else:
            network = self._config["network"]

            if isinstance(network, dict):
                # IP validation - must be present
                ip = network.get("ip")
                if ip is None:
                    errors.append("Missing required config: network.ip")
                elif not isinstance(ip, str) or not ip.startswith(("http://", "https://", "0.", "1.")):
                    errors.append(f"Invalid IP: {ip}")

                # Port validation - must be present
                port = network.get("port")
                if port is None:
                    errors.append("Missing required config: network.port")
                elif not isinstance(port, int) or port < 1024 or port > 65535:
                    errors.append(f"Invalid port: {port}")

                # Auto_reload must be boolean - must be present
                auto_reload = network.get("auto_reload")
                if auto_reload is None:
                    errors.append("Missing required config: network.auto_reload")
                elif not isinstance(auto_reload, bool):
                    errors.append(f"Invalid auto_reload value (must be boolean): {auto_reload}")

        # LLM validation - all fields required
        if "llm" not in self._config:
            errors.append("Missing 'llm' section")
        else:
            llm = self._config["llm"]
            if isinstance(llm, dict):
                model = llm.get("model")
                if model is None or model == "":
                    errors.append("Missing or empty required config: llm.model")

                base_url = llm.get("base_url")
                if base_url is None or base_url == "":
                    errors.append("Missing or empty required config: llm.base_url")

                temperature = llm.get("temperature")
                if temperature is None:
                    errors.append("Missing required config: llm.temperature")

                max_tokens = llm.get("max_tokens")
                if max_tokens is None:
                    errors.append("Missing required config: llm.max_tokens")

        # UI CSS validation - theme must be present
        if "ui_css" not in self._config:
            errors.append("Missing 'ui_css' section")
        else:
            ui = self._config["ui_css"]
            if isinstance(ui, dict):
                theme = ui.get("theme")
                if theme is None or theme not in ["soft", "default"]:
                    errors.append(f"Invalid theme: must be 'soft' or 'default', got '{theme}'")

        is_valid = len(errors) == 0
        return is_valid, errors

    def _get_nested_value(self, keys: str) -> Any:
        """Get nested configuration value by dot-separated key path. Raises KeyError if not found."""
        key_list = keys.split(".")
        value = self._config

        for k in key_list:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                raise KeyError(f"Missing required configuration: {keys}")

        return value

    def set_nested(self, keys: str, value: Any) -> None:
        """Set nested configuration value by dot-separated key path. Raises KeyError if path invalid."""
        key_list = keys.split(".")

        if len(key_list) == 1:
            self._config[key_list[0]] = value
            return

        # Navigate to parent and set/update child
        parent_key = ".".join(key_list[:-1])
        last_key = key_list[-1]

        # Get existing dict, raise KeyError if not found (no defaults)
        parent_dict = self._config.get(parent_key)
        if parent_dict is None:
            raise KeyError(f"Cannot set config value at {keys}: parent key '{parent_key}' not found")

        self._config[parent_key][last_key] = value

    def get(self, key: str) -> Any:
        """Get configuration value by dot-separated key. Raises KeyError if not found."""
        return self._get_nested_value(key)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value by dot-separated key."""
        self.set_nested(key, value)

    def update_network_config(
        self,
        host: str | None = None,
        port: int | None = None,
        auto_reload: bool | None = None,
    ) -> None:
        """Update network configuration in existing config structure."""
        if "network" not in self._config:
            raise MissingConfigError("Cannot update network config: 'network' section must be configured first")
        
        network_config = self._config["network"]

        if host is not None:
            network_config["ip"] = host
        if port is not None:
            network_config["port"] = port
        if auto_reload is not None:
            network_config["auto_reload"] = bool(auto_reload)

    def update_llm_config(
        self,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        base_url: str | None = None,
    ) -> None:
        """Update LLM configuration in existing config structure."""
        if "llm" not in self._config:
            raise MissingConfigError("Cannot update LLM config: 'llm' section must be configured first")
        
        llm_config = self._config["llm"]

        if model is not None:
            llm_config["model"] = model
        if temperature is not None:
            llm_config["temperature"] = temperature
        if max_tokens is not None:
            llm_config["max_tokens"] = max_tokens
        if base_url is not None:
            llm_config["base_url"] = base_url

    def update_repository_config(
        self,
        url: str | None = None,
        branch: str | None = None,
        enabled: bool | None = None,
        file_extensions: list[str] | None = None,
        repository_index: int | None = None,
    ) -> None:
        """Update a single repository configuration in existing config structure."""
        if "repositories" not in self._config:
            raise MissingConfigError("Cannot update repository config: 'repositories' section must be configured first")
        
        repositories = self._config["repositories"]

        if repository_index is None or 0 <= repository_index < len(repositories):
            return

        repo = repositories[repository_index]
        if isinstance(repo, dict):
            if url is not None:
                repo["url"] = url
            if branch is not None:
                repo["branch"] = branch
            if enabled is not None:
                repo["enabled"] = bool(enabled)
            if file_extensions is not None:
                repo["file_extensions"] = file_extensions

    def update_ui_config(
        self,
        theme: str | None = None,
        title: str | None = None,
        primary_color: str | None = None,
        secondary_color: str | None = None,
        background_color: str | None = None,
        text_color: str | None = None,
        font_family: str | None = None,
    ) -> None:
        """Update UI CSS configuration in existing config structure."""
        if "ui_css" not in self._config:
            raise MissingConfigError("Cannot update UI config: 'ui_css' section must be configured first")

        ui_css = self._config["ui_css"]
        if theme is not None:
            ui_css["theme"] = theme
        if title is not None:
            ui_css["title"] = title
        if primary_color is not None:
            ui_css["primary_color"] = primary_color
        if secondary_color is not None:
            ui_css["secondary_color"] = secondary_color
        if background_color is not None:
            ui_css["background_color"] = background_color
        if text_color is not None:
            ui_css["text_color"] = text_color
        if font_family is not None:
            ui_css["font_family"] = font_family

    def get_port(self) -> int:
        """Get network port - raises KeyError if not in config."""
        port = self.get("network.port")
        if isinstance(port, str):
            try:
                port = int(port)
            except ValueError:
                pass
        return int(port)

    def get_host(self) -> str:
        """Get network IP/host - raises KeyError if not in config."""
        host = self.get("network.ip")
        if isinstance(host, str) and not host.startswith(("http://", "https//")):
            return host
        raise KeyError("Network host/ip must be configured in config.json")

    def should_auto_reload(self) -> bool:
        """Check if auto-reload is enabled (for Gradio)."""
        auto_reload = self.get("network.auto_reload")
        return isinstance(auto_reload, bool) and auto_reload

    def reload_config(self) -> None:
        """Reload configuration from file without restarting application."""
        self.load_config()

    def update_from_environment(
        self,
        host: str | None = None,
        port: int | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> None:
        """Update configuration from environment variables."""
        if host is not None and "network" not in self._config:
            self._config["network"] = {}

        # Environment override for host/ip
        if host is not None:
            self._config.setdefault("network", {})["ip"] = host

        # Environment override for port (with explicit priority check)
        if port is not None:
            self._config.setdefault("network", {})["port"] = port

        # Environment override for base_url in LLM section
        if base_url is not None and "llm" not in self._config:
            self._config["llm"] = {}
        if base_url is not None:
            self._config.setdefault("llm", {})["base_url"] = base_url

    def get_config_for_ui(self) -> dict[str, Any]:
        """Get configuration formatted for UI display."""
        config = self.get_config()

        # Create a deep copy and format booleans properly for JSON serialization
        result = json.loads(json.dumps(config))

        return result