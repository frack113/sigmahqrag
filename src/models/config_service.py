# This file has been deprecated.
# Configuration is now handled by:
# - src/application/config_manager.ConfigManager
# - Direct loading from data/config/*.json files
from typing import Any


class ConfigService:
    """
    Deprecated: Use ConfigManager instead.
    
    Usage example:
        from src.application.config_manager import ConfigManager
        
        config = ConfigManager()
        app_config = config.get_app_config()
        lm_studio_config = config.get_lm_studio_config()
    """

    def __init__(self, config_path: str | None = None):
        """Deprecated - use ConfigManager instead."""
        pass

    def load_all(self) -> dict[str, Any]:
        """Use ConfigManager.read_configurations()."""
        raise DeprecationWarning("Use ConfigManager.read_configurations() instead")

    def get_app_config(self) -> dict[str, Any]:
        """Use ConfigManager.get_app_config()."""
        raise DeprecationWarning("Use ConfigManager.get_app_config() instead")


# Backward compatibility - import from application layer
try:
    from src.application.config_manager import ConfigManager

    _config_manager = None

    @classmethod
    def get_instance(cls) -> ConfigManager:
        """Get the global ConfigManager instance."""
        return cls._manager
except ImportError:
    pass