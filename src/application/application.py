"""
SigmaHQ RAG - Optimized Application Entry Point

Uses Gradio's native features:
- queue=True is set globally via gradio settings
- No custom event loop management needed
- Simple, maintainable code structure
"""

import logging
import os
from typing import Any

import gradio as gr

from src.models.config_service import ConfigService
from src.models.data_service import DataService
from src.models.rag_chat_service import RAGChatService
from src.shared.config_manager import create_config_manager

logger = logging.getLogger(__name__)

DEFAULT_CONFIG: dict[str, Any] = {
    "server": {
        "host": "0.0.0.0",
        "port": 8002,
        "base_url": "http://localhost:1234",
        "api_key": "",
    },
    "rag": {
        "embedding_model": "all-MiniLM-L6-v2",
        "chunk_size": 1000,
        "chunk_overlap": 200,
        "history_limit": 10,
    },
}


def get_logger(name: str | None = None) -> object:
    """Get or create a logger instance."""
    return logging.getLogger(name)


class SigmaHQApplication:
    """
    Unified application class for SigmaHQ RAG.

    Uses Gradio's native async support - no custom event loop needed.
    """

    def __init__(self, config_path: str | None = None):
        self.logger = logger
        self.config_path = config_path

        # Initialize shared services
        self.config_service = ConfigService()
        self.data_service = DataService()

        # Load and validate configuration
        self._initialize_config(config_path)

        # Initialize RAG/chat service
        self.rag_chat_service = self._initialize_rag_service()

        # Initialize Gradio components (lazy-loaded)
        self._init_gradio_components()

        self.app: gr.Blocks | None = None

    def _initialize_config(self, config_path: str | None = None) -> None:
        """Initialize configuration manager."""
        try:
            self.config_manager = create_config_manager(config_path)
            self.config_manager.initialize()

            if config_path and os.path.exists(config_path):
                self.config_manager.load_config(config_path)

            self.config_manager.merge_with_defaults()
            valid = self.config_manager.validate_config()

            if valid:
                self.config = self.config_manager.get_config()
            else:
                logger.warning("Configuration has validation issues, using defaults")
                self.config = DEFAULT_CONFIG.copy()

        except Exception as e:
            logger.error(f"Failed to initialize configuration: {e}")
            self.config = DEFAULT_CONFIG.copy()

    def _init_gradio_components(self) -> None:
        """Initialize Gradio UI components with lazy imports."""
        from src.components.chat_interface import ChatInterface
        from src.components.data_management import DataManagement
        from src.components.file_management import FileManagement
        from src.components.github_management import GitHubManagement
        from src.components.logs_viewer import LogsViewer

        self.chat_interface = ChatInterface(self.rag_chat_service)
        self.data_management = DataManagement(self.data_service, self.config_service)
        self.github_management = GitHubManagement()
        self.file_management = FileManagement()
        self.logs_viewer = LogsViewer()

    def _initialize_rag_service(self) -> RAGChatService:
        """Initialize RAG chat service."""
        try:
            server_config = self.config.get("server", DEFAULT_CONFIG["server"])
            base_url = server_config.get("base_url", "http://localhost:1234")

            return RAGChatService(
                base_url=base_url,
                rag_enabled=True,
                rag_n_results=3,
                rag_min_score=0.1,
                conversation_history_limit=(
                    self.config.get("rag", {}).get("history_limit", 10)
                ),
            )

        except Exception as e:
            logger.error(f"Failed to initialize RAG service: {e}")

            # Create fallback with RAG disabled
            return RAGChatService(
                rag_enabled=False,
                conversation_history_limit=10,
            )

    def _get_css(self) -> str:
        """Get custom CSS for the interface."""
        return ""

    def create_interface(self) -> gr.Blocks:
        """Create the main Gradio interface with tabs."""
        self.logger.info("Creating SigmaHQ RAG interface")

        with gr.Blocks() as self.app:
            gr.Markdown("# 🤖 SigmaHQ RAG Application")

            with gr.Blocks():
                self.chat_interface.create_tab()

                with gr.TabItem("📊 Data", id="data"):
                    self.data_management.create_tab()

                with gr.TabItem("📁 GitHub", id="github"):
                    self.github_management.create_tab()

                with gr.TabItem("📂 Files", id="files"):
                    self.file_management.create_tab()

                with gr.TabItem("⚙️ Config", id="config"):
                    from src.components.config_management import ConfigManagement

                    self.config_management = ConfigManagement(self.config_service)
                    self.config_management.create_tab()

                with gr.TabItem("📋 Logs", id="logs"):
                    self.logs_viewer.create_tab()

        return self.app

    def launch(self, port: int = 8002, dev_mode: bool = False) -> None:
        """Launch the Gradio application."""
        server_config = self.config.get("server", DEFAULT_CONFIG["server"])
        configured_port = server_config.get("port", port)

        mode_info = "development" if dev_mode else "production"
        logger.info(
            "Starting SigmaHQ RAG on port %d in %s mode",
            configured_port,
            mode_info,
        )

        # Create the interface first
        self.create_interface()

        # Launch with Gradio settings (removed deprecated reload arg)
        try:
            self.app.launch(
                server_port=configured_port,
                server_name=server_config.get("host", "0.0.0.0"),
                share=False,
                auth=None,
                theme=gr.themes.Soft(),
            )
        except OSError as e:
            if "Cannot find empty port" in str(e) or "address already in use" in str(e):
                logger.warning(
                    "Port %d is in use, trying alternatives",
                    configured_port,
                )
                for alt_port in range(configured_port + 1, configured_port + 10):
                    try:
                        self.app.launch(
                            server_port=alt_port,
                            share=False,
                            auth=None,
                        )
                        break
                    except OSError as alt_e:
                        if "address already in use" in str(alt_e):
                            continue
                        else:
                            raise
                else:
                    logger.error(
                        "Cannot find empty port in range: %d-%d",
                        configured_port,
                        configured_port + 9,
                    )
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


def create_application(config_path: str | None = None) -> SigmaHQApplication:
    """Create a configured SigmaHQ application instance."""
    return SigmaHQApplication(config_path=config_path)


def create_default_application() -> SigmaHQApplication:
    """Create an application with default configuration."""
    return create_application()
