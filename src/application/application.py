"""
SigmaHQ RAG - Simplified Application Entry Point

Uses Gradio's native features:
- queue=True is set globally via gradio settings
- No custom event loop management needed
- Simple, maintainable code structure

Configuration Requirements:
- data/config.json MUST exist at startup
- All values come from config.json - NO DEFAULT_* fallbacks
"""

import logging
from pathlib import Path
from typing import Any

import gradio as gr

from src.core.rag_service import RAGService

logger = logging.getLogger(__name__)


class MissingConfigError(Exception):
    """Raised when required configuration file is missing."""
    pass


def create_config_manager(config_path: str | None = None) -> "ConfigManager":
    """Create and initialize the configuration manager."""
    from src.shared.config_manager import ConfigManager
    
    config_file = Path(config_path) if config_path else Path("data/config.json")
    
    config_mgr = ConfigManager(str(config_file))
    try:
        config_mgr.initialize()
    except MissingConfigError as e:
        logger.error(f"Configuration required: {e}")
        raise
    
    return config_mgr


class SigmaHQApplication:
    """
    Unified application class for SigmaHQ RAG.

    Uses Gradio's native async support - no custom event loop needed.
    Requires data/config.json to exist before starting.
    All configuration values come from config.json - no fallbacks.
    """

    def __init__(self, config_path: str | Path | None = None):
        """Initialize application with configuration validation."""
        from src.models.data_service import DataService
        
        # Load and validate configuration first
        config_file = Path(config_path) if config_path else Path("data/config.json")
        
        self.config_service = create_config_manager(str(config_file))
        self.data_service = DataService()
        
        # Load configuration before anything else
        self.config = self.config_service.get_config()

    @property
    def config_manager(self) -> "ConfigManager":
        """Property to access ConfigManager instance."""
        return self.config_service

    def _get_configured_port(self) -> int:
        """Get port from network configuration."""
        return self.config["network"]["port"]

    def _get_configured_ip(self) -> str:
        """Get IP from network configuration."""
        return self.config["network"]["ip"]

    def _initialize_rag_service(self) -> "RAGService":
        """Initialize RAG service using config values."""
        llm_config = self.config["llm"]
        
        rag_service = RAGService(
            collection_name="documents",
            persist_path="data/models/chroma_db",
            model=llm_config["model"],
            base_url=llm_config["base_url"],
            temperature=llm_config["temperature"],
            max_tokens=llm_config["max_tokens"],
        )
        
        return rag_service

    def _init_gradio_components(self) -> None:
        """Initialize Gradio UI components with lazy imports."""
        from src.components.chat_interface import ChatInterface
        from src.components.data_management import DataManagement
        from src.components.file_management import FileManagement
        from src.components.github_management import GitHubManagement
        from src.components.logs_viewer import LogsViewer
        
        self.rag_chat_service = self._initialize_rag_service()
        
        self.chat_interface = ChatInterface(self.rag_chat_service)
        self.data_management = DataManagement(self.data_service, self.config_service)
        self.github_management = GitHubManagement()
        self.file_management = FileManagement()
        self.logs_viewer = LogsViewer()

    def create_interface(self) -> gr.Blocks:
        """Create the main Gradio interface with tabs using config values."""
        ui_config = self.config["ui_css"]
        title = ui_config["title"]
        theme_name = ui_config["theme"]

        from src.components.config_management import ConfigManagement

        with gr.Blocks() as self.app:
            gr.Markdown(f"# {title}")

            # Chat tab (must be first)
            with gr.TabItem("💬 Chat"):
                self.chat_interface.create_tab()

            # Data tab
            with gr.TabItem("📊 Data"):
                self.data_management.create_tab()

            # GitHub tab
            with gr.TabItem("📁 GitHub"):
                self.github_management.create_tab()

            # Files tab
            with gr.TabItem("📂 Files"):
                self.file_management.create_tab()

            # Config tab
            with gr.TabItem("⚙️ Config"):
                self.config_management = ConfigManagement(self.config_service)
                self.config_management.create_tab()

            # Logs tab
            with gr.TabItem("📋 Logs"):
                self.logs_viewer.create_tab()

        return self.app

    def launch(
        self,
        port: int | None = None,
        dev_mode: bool = False,
        reload: bool | None = None,
    ) -> None:
        """Launch the Gradio application using config values."""
        configured_port = self._get_configured_port()
        configured_ip = self._get_configured_ip()

        mode_info = "development" if dev_mode else "production"
        logger.info("Starting SigmaHQ RAG on port %d in %s mode", configured_port, mode_info)

        # Determine reload setting from config (can be overridden by parameter)
        if reload is None:
            auto_reload = self.config["network"]["auto_reload"]
            reload = isinstance(auto_reload, bool) and auto_reload

        logger.info(f"Gradio reload: {'enabled' if reload else 'disabled'}")

        try:
            # Launch with IP from config.json - NO fallback to defaults
            self.app.launch(
                server_port=configured_port,
                server_name=configured_ip,
                share=False,
                auth=None,
                theme=gr.themes.Soft(),
                reload=reload,
            )
        except OSError as e:
            if "Cannot find empty port" in str(e) or "address already in use" in str(e):
                logger.warning("Port %d is in use, trying alternatives", configured_port)

                for alt_port in range(configured_port + 1, configured_port + 20):
                    try:
                        self.app.launch(
                            server_port=alt_port,
                            server_name=configured_ip,
                            share=False,
                            auth=None,
                            theme=gr.themes.Soft(),
                            reload=reload,
                        )
                        break
                    except OSError as alt_e:
                        if "address already in use" in str(alt_e):
                            continue
                        else:
                            raise
                else:
                    logger.error("Cannot find empty port in range: %d-%d", configured_port, configured_port + 19)
                    raise
            else:
                raise

    def cleanup(self) -> None:
        """Clean up all resources."""
        try:
            logger.info("Cleanup completed")
            if hasattr(self, "rag_chat_service"):
                self.rag_chat_service.cleanup()
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


# Factory function that accepts all required parameters from config - NO DEFAULTS
def create_application(config_path: str | Path | None = None) -> SigmaHQApplication:
    """Create a configured SigmaHQ application instance (requires valid config.json)."""
    return SigmaHQApplication(config_path=config_path)