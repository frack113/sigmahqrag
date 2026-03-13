"""
Configuration Manager for SigmaHQ RAG application.

Provides configuration management and validation for the application.
"""

import json
import os
from dataclasses import dataclass
from typing import Any

from ..shared import (
    DEFAULT_CONFIG,
    SERVICE_CONFIG,
    STATUS_DEGRADED,
    STATUS_HEALTHY,
    STATUS_UNHEALTHY,
    BaseService,
)


@dataclass
class ConfigStats:
    """Statistics for configuration management."""
    config_loaded: bool = False
    config_valid: bool = False
    last_load_time: float = 0.0
    last_validation_time: float = 0.0
    validation_errors: int = 0
    last_error: str | None = None


class ConfigManager(BaseService):
    """
    Configuration manager for the application.
    
    Provides:
    - Configuration loading from files
    - Configuration validation
    - Configuration merging
    - Environment variable support
    """

    def __init__(self, config_path: str | None = None):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to configuration file
        """
        BaseService.__init__(self, f"{SERVICE_CONFIG}.config_manager")
        
        # Configuration
        self.config_path = config_path
        self.config: dict[str, Any] = {}
        
        # Statistics
        self.stats = ConfigStats()

    def load_config(self, config_path: str | None = None) -> bool:
        """
        Load configuration from file.
        
        Args:
            config_path: Path to configuration file (uses instance path if None)
            
        Returns:
            True if loading successful, False otherwise
        """
        load_path = config_path or self.config_path
        
        if not load_path:
            self.logger.error("No configuration path specified")
            return False
        
        try:
            with open(load_path) as f:
                self.config = json.load(f)
            
            self.stats.config_loaded = True
            self.stats.last_load_time = time.time()
            self.logger.info(f"Configuration loaded from {load_path}")
            
            return True
            
        except Exception as e:
            self.stats.last_error = str(e)
            self.logger.error(f"Error loading configuration from {load_path}: {e}")
            return False

    def save_config(self, config_path: str | None = None) -> bool:
        """
        Save configuration to file.
        
        Args:
            config_path: Path to save configuration file (uses instance path if None)
            
        Returns:
            True if saving successful, False otherwise
        """
        save_path = config_path or self.config_path
        
        if not save_path:
            self.logger.error("No configuration path specified for saving")
            return False
        
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            with open(save_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            self.logger.info(f"Configuration saved to {save_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving configuration to {save_path}: {e}")
            return False

    def validate_config(self) -> bool:
        """
        Validate the current configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        validation_start = time.time()
        self.stats.validation_errors = 0
        
        try:
            # Check required sections
            required_sections = [
                "llm_service",
                "rag_service", 
                "database",
                "file_processor",
                "file_storage",
            ]
            
            for section in required_sections:
                if section not in self.config:
                    self.stats.validation_errors += 1
                    self.logger.error(f"Missing required configuration section: {section}")
            
            # Validate LLM service config
            if "llm_service" in self.config:
                llm_config = self.config["llm_service"]
                if not self._validate_llm_config(llm_config):
                    self.stats.validation_errors += 1
            
            # Validate RAG service config
            if "rag_service" in self.config:
                rag_config = self.config["rag_service"]
                if not self._validate_rag_config(rag_config):
                    self.stats.validation_errors += 1
            
            # Validate database config
            if "database" in self.config:
                db_config = self.config["database"]
                if not self._validate_database_config(db_config):
                    self.stats.validation_errors += 1
            
            # Validate file processor config
            if "file_processor" in self.config:
                fp_config = self.config["file_processor"]
                if not self._validate_file_processor_config(fp_config):
                    self.stats.validation_errors += 1
            
            # Validate file storage config
            if "file_storage" in self.config:
                fs_config = self.config["file_storage"]
                if not self._validate_file_storage_config(fs_config):
                    self.stats.validation_errors += 1
            
            self.stats.config_valid = self.stats.validation_errors == 0
            self.stats.last_validation_time = time.time()
            
            if self.stats.config_valid:
                self.logger.info("Configuration validation successful")
            else:
                self.logger.error(f"Configuration validation failed with {self.stats.validation_errors} errors")
            
            return self.stats.config_valid
            
        except Exception as e:
            self.stats.last_error = str(e)
            self.logger.error(f"Configuration validation error: {e}")
            return False

    def _validate_llm_config(self, config: dict[str, Any]) -> bool:
        """Validate LLM service configuration."""
        errors = []
        
        if "base_url" not in config:
            errors.append("Missing base_url")
        
        if "api_key" not in config:
            errors.append("Missing api_key")
        
        if "timeout" in config and not isinstance(config["timeout"], int):
            errors.append("timeout must be an integer")
        
        if "max_retries" in config and not isinstance(config["max_retries"], int):
            errors.append("max_retries must be an integer")
        
        for error in errors:
            self.logger.error(f"LLM config error: {error}")
        
        return len(errors) == 0

    def _validate_rag_config(self, config: dict[str, Any]) -> bool:
        """Validate RAG service configuration."""
        errors = []
        
        if "model" not in config:
            errors.append("Missing model")
        
        if "base_url" not in config:
            errors.append("Missing base_url")
        
        if "api_key" not in config:
            errors.append("Missing api_key")
        
        if "chunk_size" in config and not isinstance(config["chunk_size"], int):
            errors.append("chunk_size must be an integer")
        
        if "chunk_overlap" in config and not isinstance(config["chunk_overlap"], int):
            errors.append("chunk_overlap must be an integer")
        
        for error in errors:
            self.logger.error(f"RAG config error: {error}")
        
        return len(errors) == 0

    def _validate_database_config(self, config: dict[str, Any]) -> bool:
        """Validate database configuration."""
        errors = []
        
        if "db_path" not in config:
            errors.append("Missing db_path")
        
        if "max_connections" in config and not isinstance(config["max_connections"], int):
            errors.append("max_connections must be an integer")
        
        if "timeout" in config and not isinstance(config["timeout"], int):
            errors.append("timeout must be an integer")
        
        for error in errors:
            self.logger.error(f"Database config error: {error}")
        
        return len(errors) == 0

    def _validate_file_processor_config(self, config: dict[str, Any]) -> bool:
        """Validate file processor configuration."""
        errors = []
        
        if "allowed_extensions" in config and not isinstance(config["allowed_extensions"], list):
            errors.append("allowed_extensions must be a list")
        
        if "max_file_size_mb" in config and not isinstance(config["max_file_size_mb"], int):
            errors.append("max_file_size_mb must be an integer")
        
        if "temp_dir" not in config:
            errors.append("Missing temp_dir")
        
        if "chunk_size" in config and not isinstance(config["chunk_size"], int):
            errors.append("chunk_size must be an integer")
        
        if "chunk_overlap" in config and not isinstance(config["chunk_overlap"], int):
            errors.append("chunk_overlap must be an integer")
        
        for error in errors:
            self.logger.error(f"File processor config error: {error}")
        
        return len(errors) == 0

    def _validate_file_storage_config(self, config: dict[str, Any]) -> bool:
        """Validate file storage configuration."""
        errors = []
        
        if "upload_dir" not in config:
            errors.append("Missing upload_dir")
        
        if "allowed_extensions" in config and not isinstance(config["allowed_extensions"], list):
            errors.append("allowed_extensions must be a list")
        
        if "max_file_size_mb" in config and not isinstance(config["max_file_size_mb"], int):
            errors.append("max_file_size_mb must be an integer")
        
        if "max_storage_size_gb" in config and not isinstance(config["max_storage_size_gb"], int):
            errors.append("max_storage_size_gb must be an integer")
        
        for error in errors:
            self.logger.error(f"File storage config error: {error}")
        
        return len(errors) == 0

    def merge_with_defaults(self) -> None:
        """Merge current configuration with default values."""
        # Use the default config structure
        defaults = DEFAULT_CONFIG
        
        for section, default_values in defaults.items():
            if section not in self.config:
                self.config[section] = default_values
            else:
                # Merge with existing config, preserving user settings
                for key, value in default_values.items():
                    if key not in self.config[section]:
                        self.config[section][key] = value

    def get_config(self) -> dict[str, Any]:
        """
        Get the current configuration.
        
        Returns:
            Configuration dictionary
        """
        return self.config.copy()

    def get_section(self, section: str) -> dict[str, Any]:
        """
        Get a specific configuration section.
        
        Args:
            section: Configuration section name
            
        Returns:
            Configuration section or empty dict if not found
        """
        return self.config.get(section, {})

    def set_section(self, section: str, config: dict[str, Any]) -> None:
        """
        Set a configuration section.
        
        Args:
            section: Configuration section name
            config: Configuration section data
        """
        self.config[section] = config

    def update_config(self, updates: dict[str, Any]) -> None:
        """
        Update configuration with new values.
        
        Args:
            updates: Dictionary of updates to merge
        """
        self.config.update(updates)

    def get_health_status(self) -> dict[str, Any]:
        """Get service health status."""
        status = STATUS_HEALTHY
        issues = []
        
        if not self.stats.config_loaded:
            status = STATUS_UNHEALTHY
            issues.append("Configuration not loaded")
        
        if not self.stats.config_valid:
            status = STATUS_DEGRADED
            issues.append(f"Configuration validation failed ({self.stats.validation_errors} errors)")
        
        return {
            "service": SERVICE_CONFIG,
            "status": status,
            "issues": issues,
            "timestamp": time.time(),
            "stats": {
                "config_loaded": self.stats.config_loaded,
                "config_valid": self.stats.config_valid,
                "last_load_time": self.stats.last_load_time,
                "last_validation_time": self.stats.last_validation_time,
                "validation_errors": self.stats.validation_errors,
                "last_error": self.stats.last_error,
            },
            "config_path": self.config_path,
        }

    def get_usage_stats(self) -> dict[str, Any]:
        """Get comprehensive usage statistics."""
        return {
            "config_path": self.config_path,
            "stats": {
                "config_loaded": self.stats.config_loaded,
                "config_valid": self.stats.config_valid,
                "last_load_time": self.stats.last_load_time,
                "last_validation_time": self.stats.last_validation_time,
                "validation_errors": self.stats.validation_errors,
                "last_error": self.stats.last_error,
            },
            "config_sections": list(self.config.keys()),
        }

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            self.logger.info("Config manager cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Error during config manager cleanup: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup()


def create_config_manager(config_path: str | None = None) -> ConfigManager:
    """Create a configuration manager with optional config path."""
    return ConfigManager(config_path=config_path)


def load_default_config() -> dict[str, Any]:
    """Load the default application configuration."""
    from .app_factory import DEFAULT_APPLICATION_CONFIG
    return DEFAULT_APPLICATION_CONFIG.copy()