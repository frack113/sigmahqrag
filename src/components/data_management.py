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
        with gr.Column() as column:
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
                self.refresh_btn = gr.Button("Refresh Statistics")
                self.reset_btn = gr.Button("Reset Database")

            # Set up event handlers
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

        # Reset database button - clears only ChromaDB vector DB
        self.reset_btn.click(
            fn=self._reset_database_wrapper,
            inputs=[],
            outputs=[self.progress_text, self.stats_display],
            queue=True,
        )

    def _update_database_wrapper(self) -> tuple[str, Any]:
        """Re-index existing files to update the vector database only."""
        if self.is_updating:
            return "Update already in progress", {}

        self.is_updating = True
        try:
            yield "Updating vector database...", {}

            # Re-index existing files from github_path to ChromaDB (vector DB only)
            reindex_result = self.data_service.reindex_vector_db()

            if reindex_result:
                updated_stats = self.data_service.get_context_stats()
                self.stats_cache = updated_stats

                success_msg = (
                    f"✅ Vector database updated! "
                    f"Re-indexed {updated_stats.get('count', 0)} documents."
                )
                yield success_msg, updated_stats
            else:
                yield "Failed to update vector database", {}

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

    def _reset_database_wrapper(self) -> tuple[str, Any]:
        """Reset the database - clears only ChromaDB collection."""
        try:
            yield "Clearing vector database...", {}

            # Clear only ChromaDB vector DB; indexed files are preserved
            reset_result = self.data_service.reset_database()

            if not reset_result:
                yield "Failed to clear the database", {}
                return

            logger.info("ChromaDB collection 'documents' cleared")
            yield "Database cleared. Run Update Database to re-index...", {}
            # Update statistics after clearing - should be 0 now
            updated_stats = self.data_service.get_context_stats()
            self.stats_cache = updated_stats

            # Statistics should remain unchanged since indexed files are NOT cleared
            stats_count = updated_stats.get("count", 0)
            if stats_count > 0:
                preserved_files = (
                    f"{stats_count} indexed files preserved" if stats_count > 0 else ""
                )
                message = (
                    "Vector DB cleared. "
                    f"{preserved_files}. "
                    "Run 'Update Database' to re-index."
                )
                yield message, updated_stats
            else:
                yield (
                    "Database cleared (vector DB only). " "Statistics refreshed.",
                    updated_stats,
                )
        except Exception as e:
            logger.error(f"Reset error: {e}")
            yield f"Error: {str(e)}", {}

    def cleanup(self) -> None:
        """Clean up resources."""
        self.is_updating = False
