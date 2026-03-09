# NiceGUI Application
from nicegui import app, ui
import os
import signal
import sys
import threading
import time

# Add current directory to Python path for imports
sys.path.insert(0, '.')

from src.nicegui_app.pages.rag_chat_page import create_rag_chat_page
from src.nicegui_app.pages.data_page import DataPage
from src.nicegui_app.pages.github_repo_page import initialize_page
from src.nicegui_app.pages.logs_page import initialize_page as initialize_logs_page
from src.nicegui_app.models.logging_service import get_logger

logger = get_logger(__name__)


# Global flag to control application shutdown
shutdown_flag = threading.Event()


def create_nicegui_app():
    """Create and run the NiceGUI application."""

    def root():
        pages = ui.sub_pages().classes("w-full h-full")
        ui.separator()

        # Header with navigation buttons
        with ui.header().classes("items-center bg-blue-100"):
            ui.button("Chat", on_click=lambda: ui.navigate.to("/")).props("flat")
            ui.button("Data", on_click=lambda: ui.navigate.to("/data")).props("flat")
            ui.button("GitHub", on_click=lambda: ui.navigate.to("/github")).props(
                "flat"
            )
            ui.button("Files", on_click=lambda: ui.navigate.to("/files")).props("flat")
            ui.button("Config", on_click=lambda: ui.navigate.to("/config")).props(
                "flat"
            )
            ui.button("Logs", on_click=lambda: ui.navigate.to("/logs")).props("flat")
            ui.space()
            ui.button("Exit", icon="logout").props("flat").on(
                "click", lambda: ui.navigate.to("/exit")
            )

        # Add pages to sub-pages
        pages.add("/", lambda: chat_page())
        pages.add("/data", lambda: data_page())
        pages.add("/github", lambda: github_page())
        pages.add("/files", lambda: files_page())
        pages.add("/config", lambda: config_page())
        pages.add("/logs", lambda: logs_page())
        pages.add("/exit", lambda: exit_page())

    def chat_page():
        """Chat page - main functionality"""
        with ui.column().classes("w-full h-screen p-0"):
            create_rag_chat_page()

    def data_page():
        """Data management and database information"""
        with ui.column().classes("w-full h-[70vh] p-4"):
            ui.markdown("""
                ### Database Management 📊
                
                This page displays database statistics and repository status.
            """)
            data = DataPage()
            data.render()

    def github_page():
        """GitHub repository management"""
        with ui.column().classes("w-full h-[70vh] p-4"):
            ui.markdown("""
                ### GitHub Repository Management 📁
                
                This page allows you to manage GitHub repositories for document analysis.
            """)
            initialize_page()

    def files_page():
        """Local files management (WIP)"""
        with ui.column().classes("w-full h-[70vh] bg-gray-100"):
            # Header
            with ui.row().classes("w-full bg-white border-b px-4 py-3 items-center"):
                ui.label("Local Files Management").classes(
                    "text-lg font-semibold text-gray-800"
                )
                ui.element("div").classes("flex-1")

            # Main content area - use flex to fill available space
            with ui.column().classes("w-full p-4 gap-4 flex-1"):
                ui.markdown("""
                    ### Local Files Management 📂
                    
                    **Work in Progress**
                    
                    This page will allow you to upload and manage local files for analysis.
                """)

    def config_page():
        """Configuration settings (WIP)"""
        with ui.column().classes("w-full h-[70vh] bg-gray-100"):
            # Header
            with ui.row().classes("w-full bg-white border-b px-4 py-3 items-center"):
                ui.label("Configuration Settings").classes(
                    "text-lg font-semibold text-gray-800"
                )
                ui.element("div").classes("flex-1")

            # Main content area - use flex to fill available space
            with ui.column().classes("w-full p-4 gap-4 flex-1"):
                ui.markdown("""
                    ### Configuration Settings ⚙️
                    
                    **Work in Progress**
                    
                    This page will allow you to configure application settings.
                """)

    def logs_page():
        """Logs viewer"""
        with ui.column().classes("w-full h-[70vh] p-4"):
            initialize_logs_page()

    def exit_page():
        """Exit confirmation page"""

        def shutdown_app():
            """Shutdown the application properly"""
            # Show shutdown notification
            ui.notify("Shutdown in progress...", type="info", position="top")

            # Signal the application to shutdown gracefully
            shutdown_flag.set()

            # Give a moment for any cleanup operations
            time.sleep(0.1)

            # Finally, shutdown the NiceGUI application
            app.shutdown()

        with ui.column().classes(
            "w-full h-screen items-center justify-center bg-gray-100"
        ):
            ui.label("Exit Application").classes(
                "text-2xl font-bold text-gray-800 mb-4"
            )
            ui.markdown("Are you sure you want to exit the application?")

            with ui.row().classes("gap-4"):
                ui.button("Yes", on_click=shutdown_app).props("color=red")
                ui.button("No", on_click=lambda: ui.navigate.to("/")).props(
                    "color=green"
                )

    # Create and run the NiceGUI application with port 8000
    logger.info("Starting SigmaHQ RAG application on port 8000")
    ui.run(
        root,
        port=8000,
        storage_secret="demo_secret_key_change_in_production",
        title="SigmaHQ RAG",
        favicon="🤖",
        reconnect_timeout=10.0,  # Increase reconnection timeout to reduce frequent messages
        binding_refresh_interval=0.5,  # Adjust binding refresh interval
        reload=False,  # Disable auto-reload to improve stability
    )


if __name__ in {"__main__", "__mp_main__"}:
    create_nicegui_app()
