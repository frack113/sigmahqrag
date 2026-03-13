"""
Environment Variables and Settings Configuration

This module provides utilities for configuring environment variables and settings
for the SigmaHQ RAG application.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class EnvironmentSetup:
    """Environment variables and settings configuration utilities."""
    
    def __init__(self, config_path: str = "data/config/environment.json"):
        """
        Initialize environment setup.
        
        Args:
            config_path: Path to the environment configuration file
        """
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
        self.logger = logging.getLogger(__name__)
        
        # Default environment variables
        self.default_env_vars = {
            # Application settings
            "APP_NAME": "SigmaHQ RAG",
            "APP_VERSION": "1.0.0",
            "DEBUG": "false",
            "LOG_LEVEL": "INFO",
            
            # Database settings
            "DATABASE_PATH": "data/local/sigmahq.db",
            "DATABASE_BACKUP_ENABLED": "true",
            "DATABASE_BACKUP_INTERVAL": "24",
            
            # LM Studio settings
            "LM_STUDIO_URL": "http://localhost:1234",
            "LM_STUDIO_TIMEOUT": "30",
            "LM_STUDIO_MAX_TOKENS": "1000",
            "LM_STUDIO_TEMPERATURE": "0.7",
            
            # Gradio settings
            "GRADIO_HOST": "0.0.0.0",
            "GRADIO_PORT": "8080",
            "GRADIO_SHARE": "false",
            "GRADIO_DEBUG": "false",
            "GRADIO_THEME": "soft",
            
            # RAG settings
            "RAG_ENABLED": "true",
            "RAG_N_RESULTS": "3",
            "RAG_MIN_SCORE": "0.1",
            "RAG_CHUNK_SIZE": "1000",
            "RAG_CHUNK_OVERLAP": "100",
            "RAG_CONVERSATION_HISTORY_LIMIT": "10",
            
            # File processing settings
            "UPLOAD_MAX_SIZE": "50",
            "UPLOAD_ALLOWED_TYPES": ".pdf,.txt,.docx,.png,.jpg,.jpeg",
            "PROCESSING_MAX_CONCURRENT": "5",
            "TEMP_DIR": "data/local/temp",
            
            # GitHub settings
            "GITHUB_TOKEN": "",
            "GITHUB_CLONE_TIMEOUT": "300",
            "GITHUB_MAX_REPOS": "10",
            
            # Security settings
            "ALLOWED_HOSTS": "*",
            "CORS_ORIGINS": "*",
            "SESSION_TIMEOUT": "3600",
            
            # Performance settings
            "MAX_MEMORY_USAGE": "2048",
            "CACHE_ENABLED": "true",
            "CACHE_TTL": "3600",
            "STREAMING_ENABLED": "true"
        }
    
    def ensure_config_directory(self) -> bool:
        """
        Ensure the configuration directory exists.
        
        Returns:
            True if directory exists or was created successfully
        """
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.logger.info(f"Configuration directory ensured: {self.config_dir}")
            return True
        except Exception as e:
            self.logger.error(f"Error creating configuration directory: {e}")
            return False
    
    def create_environment_config(self) -> bool:
        """
        Create the environment configuration file.
        
        Returns:
            True if configuration file created successfully
        """
        try:
            if not self.ensure_config_directory():
                return False
            
            config = {
                "application": {
                    "name": self.default_env_vars["APP_NAME"],
                    "version": self.default_env_vars["APP_VERSION"],
                    "debug": self.default_env_vars["DEBUG"].lower() == "true",
                    "log_level": self.default_env_vars["LOG_LEVEL"]
                },
                "database": {
                    "path": self.default_env_vars["DATABASE_PATH"],
                    "backup_enabled": self.default_env_vars["DATABASE_BACKUP_ENABLED"].lower() == "true",
                    "backup_interval_hours": int(self.default_env_vars["DATABASE_BACKUP_INTERVAL"])
                },
                "lm_studio": {
                    "url": self.default_env_vars["LM_STUDIO_URL"],
                    "timeout": int(self.default_env_vars["LM_STUDIO_TIMEOUT"]),
                    "max_tokens": int(self.default_env_vars["LM_STUDIO_MAX_TOKENS"]),
                    "temperature": float(self.default_env_vars["LM_STUDIO_TEMPERATURE"])
                },
                "gradio": {
                    "host": self.default_env_vars["GRADIO_HOST"],
                    "port": int(self.default_env_vars["GRADIO_PORT"]),
                    "share": self.default_env_vars["GRADIO_SHARE"].lower() == "true",
                    "debug": self.default_env_vars["GRADIO_DEBUG"].lower() == "true",
                    "theme": self.default_env_vars["GRADIO_THEME"]
                },
                "rag": {
                    "enabled": self.default_env_vars["RAG_ENABLED"].lower() == "true",
                    "n_results": int(self.default_env_vars["RAG_N_RESULTS"]),
                    "min_score": float(self.default_env_vars["RAG_MIN_SCORE"]),
                    "chunk_size": int(self.default_env_vars["RAG_CHUNK_SIZE"]),
                    "chunk_overlap": int(self.default_env_vars["RAG_CHUNK_OVERLAP"]),
                    "conversation_history_limit": int(self.default_env_vars["RAG_CONVERSATION_HISTORY_LIMIT"])
                },
                "file_processing": {
                    "upload_max_size_mb": int(self.default_env_vars["UPLOAD_MAX_SIZE"]),
                    "allowed_types": self.default_env_vars["UPLOAD_ALLOWED_TYPES"].split(","),
                    "max_concurrent": int(self.default_env_vars["PROCESSING_MAX_CONCURRENT"]),
                    "temp_dir": self.default_env_vars["TEMP_DIR"]
                },
                "github": {
                    "token": self.default_env_vars["GITHUB_TOKEN"],
                    "clone_timeout": int(self.default_env_vars["GITHUB_CLONE_TIMEOUT"]),
                    "max_repos": int(self.default_env_vars["GITHUB_MAX_REPOS"])
                },
                "security": {
                    "allowed_hosts": self.default_env_vars["ALLOWED_HOSTS"].split(","),
                    "cors_origins": self.default_env_vars["CORS_ORIGINS"].split(","),
                    "session_timeout": int(self.default_env_vars["SESSION_TIMEOUT"])
                },
                "performance": {
                    "max_memory_usage_mb": int(self.default_env_vars["MAX_MEMORY_USAGE"]),
                    "cache_enabled": self.default_env_vars["CACHE_ENABLED"].lower() == "true",
                    "cache_ttl": int(self.default_env_vars["CACHE_TTL"]),
                    "streaming_enabled": self.default_env_vars["STREAMING_ENABLED"].lower() == "true"
                }
            }
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, default=str)
            
            self.logger.info(f"Environment configuration created: {self.config_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating environment configuration: {e}")
            return False
    
    def load_environment_config(self) -> dict[str, Any] | None:
        """
        Load the environment configuration from file.
        
        Returns:
            Dictionary with configuration or None if loading failed
        """
        try:
            if not self.config_path.exists():
                self.logger.warning(f"Configuration file not found: {self.config_path}")
                return None
            
            with open(self.config_path, encoding='utf-8') as f:
                config = json.load(f)
            
            self.logger.info(f"Environment configuration loaded: {self.config_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"Error loading environment configuration: {e}")
            return None
    
    def set_environment_variables(self) -> bool:
        """
        Set environment variables from configuration file.
        
        Returns:
            True if environment variables set successfully
        """
        try:
            config = self.load_environment_config()
            if not config:
                self.logger.warning("No configuration loaded, using defaults")
                config = self._get_default_config()
            
            # Set environment variables
            for section_name, section_config in config.items():
                for key, value in section_config.items():
                    env_key = f"{section_name.upper()}_{key.upper()}"
                    env_value = str(value)
                    os.environ[env_key] = env_value
            
            # Set individual environment variables for backward compatibility
            for key, value in self.default_env_vars.items():
                os.environ[key] = value
            
            self.logger.info("Environment variables set successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error setting environment variables: {e}")
            return False
    
    def _get_default_config(self) -> dict[str, Any]:
        """Get default configuration structure."""
        return {
            "application": {
                "name": self.default_env_vars["APP_NAME"],
                "version": self.default_env_vars["APP_VERSION"],
                "debug": self.default_env_vars["DEBUG"].lower() == "true",
                "log_level": self.default_env_vars["LOG_LEVEL"]
            },
            "database": {
                "path": self.default_env_vars["DATABASE_PATH"],
                "backup_enabled": self.default_env_vars["DATABASE_BACKUP_ENABLED"].lower() == "true",
                "backup_interval_hours": int(self.default_env_vars["DATABASE_BACKUP_INTERVAL"])
            },
            "lm_studio": {
                "url": self.default_env_vars["LM_STUDIO_URL"],
                "timeout": int(self.default_env_vars["LM_STUDIO_TIMEOUT"]),
                "max_tokens": int(self.default_env_vars["LM_STUDIO_MAX_TOKENS"]),
                "temperature": float(self.default_env_vars["LM_STUDIO_TEMPERATURE"])
            },
            "gradio": {
                "host": self.default_env_vars["GRADIO_HOST"],
                "port": int(self.default_env_vars["GRADIO_PORT"]),
                "share": self.default_env_vars["GRADIO_SHARE"].lower() == "true",
                "debug": self.default_env_vars["GRADIO_DEBUG"].lower() == "true",
                "theme": self.default_env_vars["GRADIO_THEME"]
            },
            "rag": {
                "enabled": self.default_env_vars["RAG_ENABLED"].lower() == "true",
                "n_results": int(self.default_env_vars["RAG_N_RESULTS"]),
                "min_score": float(self.default_env_vars["RAG_MIN_SCORE"]),
                "chunk_size": int(self.default_env_vars["RAG_CHUNK_SIZE"]),
                "chunk_overlap": int(self.default_env_vars["RAG_CHUNK_OVERLAP"]),
                "conversation_history_limit": int(self.default_env_vars["RAG_CONVERSATION_HISTORY_LIMIT"])
            },
            "file_processing": {
                "upload_max_size_mb": int(self.default_env_vars["UPLOAD_MAX_SIZE"]),
                "allowed_types": self.default_env_vars["UPLOAD_ALLOWED_TYPES"].split(","),
                "max_concurrent": int(self.default_env_vars["PROCESSING_MAX_CONCURRENT"]),
                "temp_dir": self.default_env_vars["TEMP_DIR"]
            },
            "github": {
                "token": self.default_env_vars["GITHUB_TOKEN"],
                "clone_timeout": int(self.default_env_vars["GITHUB_CLONE_TIMEOUT"]),
                "max_repos": int(self.default_env_vars["GITHUB_MAX_REPOS"])
            },
            "security": {
                "allowed_hosts": self.default_env_vars["ALLOWED_HOSTS"].split(","),
                "cors_origins": self.default_env_vars["CORS_ORIGINS"].split(","),
                "session_timeout": int(self.default_env_vars["SESSION_TIMEOUT"])
            },
            "performance": {
                "max_memory_usage_mb": int(self.default_env_vars["MAX_MEMORY_USAGE"]),
                "cache_enabled": self.default_env_vars["CACHE_ENABLED"].lower() == "true",
                "cache_ttl": int(self.default_env_vars["CACHE_TTL"]),
                "streaming_enabled": self.default_env_vars["STREAMING_ENABLED"].lower() == "true"
            }
        }
    
    def get_environment_info(self) -> dict[str, Any]:
        """
        Get information about the current environment setup.
        
        Returns:
            Dictionary with environment information
        """
        info = {
            "config_file_exists": self.config_path.exists(),
            "config_file_path": str(self.config_path),
            "config_directory_exists": self.config_dir.exists(),
            "environment_variables_set": False,
            "loaded_config": None,
            "validation_results": {}
        }
        
        # Load configuration
        config = self.load_environment_config()
        info["loaded_config"] = config
        
        # Validate configuration
        if config:
            info["environment_variables_set"] = self.set_environment_variables()
            info["validation_results"] = self.validate_configuration(config)
        
        return info
    
    def validate_configuration(self, config: dict[str, Any]) -> dict[str, bool]:
        """
        Validate the configuration values.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_results = {}
        
        # Validate application settings
        app_config = config.get("application", {})
        validation_results["app_name"] = isinstance(app_config.get("name"), str) and len(app_config.get("name", "")) > 0
        validation_results["app_version"] = isinstance(app_config.get("version"), str) and len(app_config.get("version", "")) > 0
        validation_results["debug"] = isinstance(app_config.get("debug"), bool)
        validation_results["log_level"] = app_config.get("log_level") in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        # Validate database settings
        db_config = config.get("database", {})
        validation_results["database_path"] = isinstance(db_config.get("path"), str) and len(db_config.get("path", "")) > 0
        validation_results["backup_enabled"] = isinstance(db_config.get("backup_enabled"), bool)
        validation_results["backup_interval"] = isinstance(db_config.get("backup_interval_hours"), int) and db_config.get("backup_interval_hours") > 0
        
        # Validate LM Studio settings
        lm_config = config.get("lm_studio", {})
        validation_results["lm_studio_url"] = isinstance(lm_config.get("url"), str) and len(lm_config.get("url", "")) > 0
        validation_results["lm_studio_timeout"] = isinstance(lm_config.get("timeout"), int) and lm_config.get("timeout") > 0
        validation_results["lm_studio_max_tokens"] = isinstance(lm_config.get("max_tokens"), int) and lm_config.get("max_tokens") > 0
        validation_results["lm_studio_temperature"] = isinstance(lm_config.get("temperature"), (int, float)) and 0 <= lm_config.get("temperature") <= 2
        
        # Validate Gradio settings
        gradio_config = config.get("gradio", {})
        validation_results["gradio_host"] = isinstance(gradio_config.get("host"), str) and len(gradio_config.get("host", "")) > 0
        validation_results["gradio_port"] = isinstance(gradio_config.get("port"), int) and 1024 <= gradio_config.get("port") <= 65535
        validation_results["gradio_share"] = isinstance(gradio_config.get("share"), bool)
        validation_results["gradio_debug"] = isinstance(gradio_config.get("debug"), bool)
        validation_results["gradio_theme"] = isinstance(gradio_config.get("theme"), str) and len(gradio_config.get("theme", "")) > 0
        
        # Validate RAG settings
        rag_config = config.get("rag", {})
        validation_results["rag_enabled"] = isinstance(rag_config.get("enabled"), bool)
        validation_results["rag_n_results"] = isinstance(rag_config.get("n_results"), int) and rag_config.get("n_results") > 0
        validation_results["rag_min_score"] = isinstance(rag_config.get("min_score"), (int, float)) and 0 <= rag_config.get("min_score") <= 1
        validation_results["rag_chunk_size"] = isinstance(rag_config.get("chunk_size"), int) and rag_config.get("chunk_size") > 0
        validation_results["rag_chunk_overlap"] = isinstance(rag_config.get("chunk_overlap"), int) and rag_config.get("chunk_overlap") >= 0
        validation_results["rag_conversation_limit"] = isinstance(rag_config.get("conversation_history_limit"), int) and rag_config.get("conversation_history_limit") > 0
        
        return validation_results
    
    def create_environment_summary(self) -> str:
        """
        Create a summary of the environment configuration.
        
        Returns:
            String with environment summary
        """
        info = self.get_environment_info()
        config = info.get("loaded_config", {})
        
        summary = []
        summary.append("=== Environment Configuration Summary ===")
        summary.append(f"Config File: {info['config_file_path']}")
        summary.append(f"Config Exists: {info['config_file_exists']}")
        summary.append(f"Environment Variables Set: {info['environment_variables_set']}")
        summary.append("")
        
        if config:
            for section_name, section_config in config.items():
                summary.append(f"--- {section_name.upper()} ---")
                for key, value in section_config.items():
                    summary.append(f"  {key}: {value}")
                summary.append("")
        
        return "\n".join(summary)
    
    def initialize_environment(self) -> dict[str, Any]:
        """
        Complete environment initialization process.
        
        Returns:
            Dictionary with initialization results
        """
        results = {
            "config_directory_created": False,
            "config_file_created": False,
            "environment_variables_set": False,
            "configuration_validated": False,
            "environment_info": {}
        }
        
        self.logger.info("Starting environment initialization...")
        
        # Step 1: Ensure config directory exists
        results["config_directory_created"] = self.ensure_config_directory()
        
        # Step 2: Create environment config
        if results["config_directory_created"]:
            results["config_file_created"] = self.create_environment_config()
        
        # Step 3: Set environment variables
        if results["config_file_created"]:
            results["environment_variables_set"] = self.set_environment_variables()
        
        # Step 4: Validate configuration
        if results["environment_variables_set"]:
            results["configuration_validated"] = True
        
        # Get environment info
        results["environment_info"] = self.get_environment_info()
        
        self.logger.info("Environment initialization completed")
        return results


def setup_environment() -> dict[str, Any]:
    """
    Convenience function to set up the environment.
    
    Returns:
        Dictionary with setup results
    """
    env_setup = EnvironmentSetup()
    return env_setup.initialize_environment()


if __name__ == "__main__":
    # Test environment setup
    results = setup_environment()
    print("Environment Setup Results:")
    for key, value in results.items():
        if key != "environment_info":
            print(f"  {key}: {value}")
    
    print("\nEnvironment Summary:")
    env_setup = EnvironmentSetup()
    print(env_setup.create_environment_summary())