"""
SigmaHQ RAG - Simplified Application Entry Point

Uses Gradio's native features for async operations.
Port conflicts will be reported as errors (no automatic retry).
"""

import logging
from pathlib import Path
from typing import Any

import gradio as gr

from src.shared.config_manager import create_config_manager
from src.shared.constants import DATA_CHROMA_PATH
from src.shared.css import get_css
from src.core.rag_service import RAGService
from src.models.data_service import DataService

logger = logging.getLogger(__name__)


class SigmaHQApplication:
    """Main application class for SigmaHQ RAG."""

    def __init__(self, config_path: str | Path | None = None):
        """Initialize application with configuration validation."""
        config_file = Path(config_path) if config_path else Path("data/config.json")
        self.config_manager = create_config_manager(str(config_file))
        self._config_data: dict[str, Any] = self.config_manager.get_config()

        # Optional services - initialized when interface is created
        self.interface: gr.Blocks | None = None
        
        logger.info(f"Configuration loaded from {config_file}")

    @property
    def config(self) -> dict[str, Any]:
        """Property to access configuration data."""
        return self._config_data


    def initialize_services(self):
        """Initialize all application services."""
        from src.components.chat_interface import ChatInterface
        from src.components.data_management import DataManagement
        from src.components.file_management import FileManagement
        from src.components.github_management import GitHubManagement
        from src.components.logs_viewer import LogsViewer
        from src.components.config_management import ConfigManagement

        self.rag_chat_service = RAGService(
            collection_name="documents",
            persist_path=DATA_CHROMA_PATH,
        )

        self.data_service = DataService()
        self.chat_interface = ChatInterface(self.rag_chat_service)
        self.github_management = GitHubManagement()
        self.file_management = FileManagement()
        self.logs_viewer = LogsViewer()
        
        # Assign data_management and config_management instances
        self.data_management = DataManagement(self.data_service, self.config_manager)
        self.config_management = ConfigManagement(config_service=self.config_manager)

        return (
            self.chat_interface,
            self.data_management,
            self.github_management,
            self.file_management,
            self.config_management,
            self.logs_viewer,
        )

    def _get_custom_css(self) -> str:
        """Return custom CSS for dynamic, responsive UI styling."""
        return get_css()
    def create_interface(self) -> gr.Blocks:
        """Create the main Gradio interface with tabs using config values."""
        ui_config = self.config["ui_css"]
        title = ui_config["title"]

        (
            self.chat_interface,
            self.data_management,
            self.github_management,
            self.file_management,
            self.config_management,
            self.logs_viewer,
        ) = self.initialize_services()

        with gr.Blocks(theme=gr.themes.Soft()) as interface:
            gr.Markdown(f"# {title}")

            with gr.TabItem("💬 Chat"):
                self.chat_interface.create_tab()
            with gr.TabItem("📊 Data"):
                self.data_management.create_tab()
            with gr.TabItem("📁 GitHub"):
                self.github_management.create_tab()
            with gr.TabItem("📂 Files"):
                self.file_management.create_tab()
            with gr.TabItem("⚙️ Config"):
                self.config_management.create_tab()
            with gr.TabItem("📋 Logs"):
                self.logs_viewer.create_tab()

        return interface

    def launch(self) -> None:
        """Launch the Gradio application."""
        port = self.config["network"]["port"]
        host = self.config["network"]["ip"]

        logger.info(f"Starting SigmaHQ RAG on {host}:{port}")

        # Create interface and launch with error display enabled and theme parameter
        self.interface = self.create_interface()
        self.interface.launch(
            server_port=port,
            server_name=host,
            show_error=True,
            css=self._get_custom_css(),
        )
