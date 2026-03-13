"""
Data Management Component - Native Gradio Features

Uses Gradio's native features:
- gr.JSON component for statistics display
- Simple async event handlers with queue=True
- No manual event loop management
"""

import logging
from typing import Any

import gradio as gr
from src.models.config_service import ConfigService
from src.models.data_service import DataService

logger = logging.getLogger(__name__)


class DataManagement:
    """
    Data management component using Gradio's native features.

    Features:
    - Database statistics display via gr.JSON
    - Async operations via Gradio queue (queue=True)
    - Real-time status updates with yield
    """

    def __init__(self, data_service: DataService, config_service: ConfigService):
        self.data_service = data_service
        self.config_service = config_service

        self.is_updating = False
        self.stats_cache: dict[str, Any] = {}

    def create_tab(self) -> None:
        """Create the data management tab with native Gradio components."""
        with gr.Column(elem_classes="data-container") as column:
            gr.Markdown("### Database Statistics 📊")

            # Statistics display using JSON component
            self.stats_display = gr.JSON(value={}, label="Database Statistics")

            # Progress display - native Gradio textbox
            self.progress_text = gr.Textbox(
                label="Progress", interactive=False, value="Ready"
            )

            # Buttons row with native styling
            with gr.Row():
                self.update_btn = gr.Button("Update Database", variant="primary")
                self.refresh_btn = gr.Button("Refresh Stats")
                self.clear_btn = gr.Button("Clear Context")

            self._setup_event_handlers(column)

    def _setup_event_handlers(self, column: gr.Column):
        """Set up event handlers using Gradio's native pattern."""

        # Update database button - async with yield for progress
        self.update_btn.click(
            fn=self._update_database_wrapper,
            inputs=[],
            outputs=[self.progress_text, self.stats_display],
            queue=True,  # Native queuing for async operations
        )

        # Refresh stats button
        self.refresh_btn.click(
            fn=self._refresh_data_wrapper,
            inputs=[],
            outputs=[self.progress_text, self.stats_display],
            queue=True,
        )

        # Clear context button
        self.clear_btn.click(
            fn=self._clear_context_wrapper,
            inputs=[],
            outputs=[self.progress_text, self.stats_display],
            queue=True,
        )

    def _update_database_wrapper(self) -> tuple[str, Any]:
        """Update the knowledge base with progress tracking."""
        if self.is_updating:
            return "Update already in progress", {}

        self.is_updating = True
        try:
            # Step 1: Load configuration
            yield "Loading configuration...", {}

            repo_config = self.data_service.get_repo_config()

            if not repo_config["repositories"]:
                yield "No repositories configured", {}
                return

            enabled_repos = [
                repo for repo in repo_config["repositories"] if repo["enabled"]
            ]

            if not enabled_repos:
                yield "No enabled repositories found", {}
                return

            # Step 2: Clone repositories
            yield f"Updating {len(enabled_repos)} repositories...", {}

            clone_result = self.data_service.clone_enabled_repositories(repo_config)

            if not clone_result:
                yield "Failed to update repositories", {}
                return

            # Step 3: Index repositories
            yield "Indexing repository content...", {}

            index_result = self.data_service.index_enabled_repositories(repo_config)

            if index_result:
                updated_stats = self.data_service.get_context_stats()
                self.stats_cache = updated_stats

                success_msg = (
                    f"✅ Knowledge base updated! "
                    f"Indexed {updated_stats.get('count', 0)} documents from "
                    f"{len(enabled_repos)} repositories."
                )
                yield success_msg, updated_stats
            else:
                yield "No repositories were indexed", {}

        except Exception as e:
            logger.error(f"Update error: {e}")
            yield f"Error: {str(e)}", {}
        finally:
            self.is_updating = False

    def _refresh_data_wrapper(self) -> tuple[str, Any]:
        """Refresh the statistics display."""
        try:
            stats = self.data_service.get_context_stats()
            self.stats_cache = stats
            yield "Data refreshed!", stats
        except Exception as e:
            logger.error(f"Refresh error: {e}")
            yield f"Error: {str(e)}", {}

    def _clear_context_wrapper(self) -> tuple[str, Any]:
        """Clear the RAG context."""
        try:
            success = self.data_service.clear_context()

            if success:
                updated_stats = self.data_service.get_context_stats()
                self.stats_cache = updated_stats
                yield "Context cleared!", updated_stats
            else:
                yield "Failed to clear context", {}
        except Exception as e:
            logger.error(f"Clear error: {e}")
            yield f"Error: {str(e)}", {}

    def cleanup(self):
        """Clean up resources."""
        self.is_updating = False
