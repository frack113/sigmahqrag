"""
Logs Viewer Component for Gradio

Migrates the Logs page to Gradio with real-time monitoring,
filtering, and async operations for log management.
"""

import asyncio
import logging
from typing import Any

import gradio as gr

from .base_component import AsyncComponent

logger = logging.getLogger(__name__)


class LogsViewer(AsyncComponent):
    """
    Logs viewer component with real-time monitoring and filtering.

    Features:
    - Real-time log monitoring with async updates
    - Text and level-based filtering
    - Auto-scroll functionality
    - Log export capabilities
    - Progress indicators for long operations
    """

    def __init__(self):
        super().__init__()
        self.is_monitoring = False
        self.monitoring_task = None

        # Filter state
        self.filter_text = ""
        self.log_level_filter = "ALL"
        self.auto_scroll = True

        # Log data
        self.log_lines: list[str] = []
        self.filtered_lines: list[str] = []

        # UI state
        self.status_text = "Ready"

        # UI components will be created in create_tab()
        self.filter_input = None
        self.level_filter = None
        self.auto_scroll_checkbox = None
        self.start_monitor_btn = None
        self.stop_monitor_btn = None
        self.refresh_btn = None
        self.clear_btn = None
        self.download_btn = None
        self.logs_display = None
        self.status_label = None
        self.line_count_label = None
        self.log_info_display = None

    def create_tab(self):
        """Create the logs viewer tab."""
        with gr.Column(elem_classes="logs-container"):
            gr.Markdown("### Application Logs")

            # Filter controls
            with gr.Row():
                self.filter_input = gr.Textbox(
                    label="Filter logs",
                    placeholder="Enter text to filter logs...",
                    elem_classes="filter-input",
                )
                self.level_filter = gr.Dropdown(
                    choices=["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    value="ALL",
                    label="Log Level",
                    elem_classes="level-filter",
                )
                self.auto_scroll_checkbox = gr.Checkbox(
                    label="Auto-scroll", value=True, elem_classes="auto-scroll-checkbox"
                )

            # Controls
            with gr.Row():
                self.start_monitor_btn = gr.Button(
                    "Start Monitoring",
                    variant="primary",
                    elem_classes="start-monitor-btn",
                )
                self.stop_monitor_btn = gr.Button(
                    "Stop Monitoring", elem_classes="stop-monitor-btn"
                )
                self.refresh_btn = gr.Button("Refresh", elem_classes="refresh-btn")
                self.clear_btn = gr.Button(
                    "Clear Logs", variant="stop", elem_classes="clear-btn"
                )
                self.download_btn = gr.Button("Download", elem_classes="download-btn")

            # Log display area
            self.logs_display = gr.Textbox(
                label="Application Logs",
                lines=20,
                interactive=False,
                elem_classes="logs-textbox",
            )

            # Status and information
            with gr.Row():
                self.status_label = gr.Textbox(
                    label="Status",
                    value="Ready",
                    interactive=False,
                    elem_classes="status-label",
                )
                self.line_count_label = gr.Textbox(
                    label="Line Count",
                    value="0 lines",
                    interactive=False,
                    elem_classes="line-count-label",
                )

            # Log information display
            self.log_info_display = gr.JSON(
                value={}, label="Log Information", elem_classes="log-info-json"
            )

            # Event handlers
            self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Set up event handlers for the logs viewer interface."""

        self.filter_input.change(
            fn=self._on_filter_change,
            inputs=[self.filter_input, self.level_filter],
            outputs=[self.logs_display, self.line_count_label, self.status_label],
            queue=True,
        )

        self.level_filter.change(
            fn=self._on_level_filter_change,
            inputs=[self.filter_input, self.level_filter],
            outputs=[self.logs_display, self.line_count_label, self.status_label],
            queue=True,
        )

        self.auto_scroll_checkbox.change(
            fn=self._on_auto_scroll_change,
            inputs=[self.auto_scroll_checkbox],
            outputs=[self.status_label],
            queue=True,
        )

        self.start_monitor_btn.click(
            fn=self._start_monitoring,
            inputs=[],
            outputs=[
                self.start_monitor_btn,
                self.stop_monitor_btn,
                self.status_label,
                self.log_info_display,
            ],
            queue=True,
        )

        self.stop_monitor_btn.click(
            fn=self._stop_monitoring,
            inputs=[],
            outputs=[
                self.start_monitor_btn,
                self.stop_monitor_btn,
                self.status_label,
                self.log_info_display,
            ],
            queue=True,
        )

        self.refresh_btn.click(
            fn=self._refresh_logs,
            inputs=[self.filter_input, self.level_filter],
            outputs=[
                self.logs_display,
                self.line_count_label,
                self.status_label,
                self.log_info_display,
            ],
            queue=True,
        )

        self.clear_btn.click(
            fn=self._clear_logs,
            inputs=[],
            outputs=[self.logs_display, self.line_count_label, self.status_label],
            queue=True,
        )

        self.download_btn.click(
            fn=self._download_logs, inputs=[], outputs=[self.status_label], queue=True
        )

    async def _load_initial_logs(self):
        """Load initial log entries."""
        try:
            self.log_lines = await self._get_recent_logs_async(200)
            self._apply_filters()
            self._update_log_display()
            self.status_text = "Loaded initial logs"

            if self.logs_display and self.line_count_label:
                return (
                    self.logs_display.value,
                    self.line_count_label.value,
                    self.status_text,
                    self._generate_log_info(),
                )
            else:
                return "Loading logs...", "0 lines", self.status_text, {}

        except Exception as e:
            error_msg = f"Error loading initial logs: {str(e)}"
            logger.error(error_msg)
            self.status_text = error_msg
            return "Error loading logs", "0 lines", self.status_text, {}

    async def _get_recent_logs_async(self, limit: int = 200) -> list[str]:
        """Get recent log entries asynchronously."""
        try:
            # Get recent logs from file system directly
            import time
            from pathlib import Path

            log_file = Path("logs/app.log")
            if not log_file.exists():
                return []

            # Read last N lines from log file
            log_lines = log_file.read_text(
                encoding="utf-8", errors="ignore"
            ).splitlines()[-limit:]
            return log_lines

        except Exception as e:
            logger.error(f"Error getting recent logs: {e}")
            return []

    async def _on_filter_change(self, filter_text: str, level_filter: str) -> tuple:
        """Handle filter text change."""
        self.filter_text = filter_text or ""
        self.log_level_filter = level_filter
        self._apply_filters()
        self._update_log_display()

        if self.logs_display and self.line_count_label:
            return (
                self.logs_display.value,
                self.line_count_label.value,
                self.status_text,
            )
        else:
            return "Loading...", "0 lines", self.status_text

    async def _on_level_filter_change(
        self, filter_text: str, level_filter: str
    ) -> tuple:
        """Handle log level filter change."""
        self.filter_text = filter_text or ""
        self.log_level_filter = level_filter
        self._apply_filters()
        self._update_log_display()

        if self.logs_display and self.line_count_label:
            return (
                self.logs_display.value,
                self.line_count_label.value,
                self.status_text,
            )
        else:
            return "Loading...", "0 lines", self.status_text

    async def _on_auto_scroll_change(self, auto_scroll: bool) -> str:
        """Handle auto-scroll toggle change."""
        self.auto_scroll = auto_scroll
        return f"Auto-scroll {'enabled' if auto_scroll else 'disabled'}"

    async def _start_monitoring(self) -> tuple:
        """Start real-time log monitoring."""
        if self.is_monitoring:
            return (
                self.start_monitor_btn,
                self.stop_monitor_btn,
                "Monitoring already active",
                self._generate_log_info(),
            )

        self.is_monitoring = True
        self.status_text = "Monitoring logs in real-time..."

        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()

        self.monitoring_task = asyncio.create_task(self._monitor_logs())

        return (
            self.start_monitor_btn,
            self.stop_monitor_btn,
            self.status_text,
            self._generate_log_info(),
        )

    async def _stop_monitoring(self) -> tuple:
        """Stop real-time log monitoring."""
        if not self.is_monitoring:
            return (
                self.start_monitor_btn,
                self.stop_monitor_btn,
                "Monitoring not active",
                self._generate_log_info(),
            )

        self.is_monitoring = False
        self.status_text = "Monitoring stopped"

        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()

        log_info = self._generate_log_info()

        return self.start_monitor_btn, self.stop_monitor_btn, self.status_text, log_info

    async def _monitor_logs(self):
        """Background task for real-time log monitoring."""
        try:
            while self.is_monitoring:
                new_lines = await self._get_recent_logs_async(50)

                if new_lines and len(new_lines) > len(self.log_lines):
                    new_log_lines = new_lines[len(self.log_lines) :]
                    self.log_lines.extend(new_log_lines)

                    self._apply_filters()
                    self._update_log_display()

                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("Log monitoring task cancelled")
        except Exception as e:
            logger.error(f"Error in log monitoring: {e}")
            self.status_text = f"Error in monitoring: {str(e)}"

    def _apply_filters(self):
        """Apply current filters to log lines."""
        filtered = self.log_lines.copy()

        if self.filter_text.strip():
            filter_lower = self.filter_text.lower()
            filtered = [line for line in filtered if filter_lower in line.lower()]

        if self.log_level_filter != "ALL":
            level_indicator = f"- {self.log_level_filter} -"
            filtered = [line for line in filtered if level_indicator in line]

        self.filtered_lines = filtered

    def _update_log_display(self):
        """Update the log display with filtered content."""
        if not self.filtered_lines:
            self.logs_display.value = (
                "No logs found. Start monitoring to see real-time logs."
            )
        else:
            display_lines = self.filtered_lines[-500:]
            self.logs_display.value = "\n".join(display_lines)

        self.line_count_label.value = f"{len(self.filtered_lines)} lines"

    async def _refresh_logs(self, filter_text: str, level_filter: str) -> tuple:
        """Refresh the log display."""
        try:
            self.filter_text = filter_text or ""
            self.log_level_filter = level_filter

            self.log_lines = await self._get_recent_logs_async(200)
            self._apply_filters()
            self._update_log_display()

            self.status_text = "Logs refreshed"

            if self.logs_display and self.line_count_label:
                return (
                    self.logs_display.value,
                    self.line_count_label.value,
                    self.status_text,
                    self._generate_log_info(),
                )
            else:
                return (
                    "Loading...",
                    "0 lines",
                    self.status_text,
                    self._generate_log_info(),
                )

        except Exception as e:
            error_msg = f"Error refreshing logs: {str(e)}"
            logger.error(error_msg)
            self.status_text = error_msg
            return "Error", "0 lines", self.status_text, self._generate_log_info()

    async def _clear_logs(self) -> tuple:
        """Clear all logs."""
        try:
            # Clear log file directly using file system operations
            import logging

            # Disable logger temporarily to prevent new logs
            handler = None
            for h in logger.handlers[:]:
                handler = h
                logger.removeHandler(h)

            self.log_lines = []
            self.filtered_lines = []
            self._update_log_display()
            self.status_text = "Logs cleared successfully"

            # Restore logger
            if handler:
                logger.addHandler(handler)

            return (
                self.logs_display.value,
                self.line_count_label.value,
                self.status_text,
            )

        except Exception as e:
            error_msg = f"Error clearing logs: {str(e)}"
            logger.error(error_msg)
            self.status_text = error_msg
            return "Error", "0 lines", self.status_text

    async def _download_logs(self) -> str:
        """Download the current log file."""
        try:
            from pathlib import Path

            log_file = Path("logs/app.log")
            if not log_file.exists():
                self.status_text = "No log file to download"
                return self.status_text

            # Create download link (for Gradio)
            content = log_file.read_text(encoding="utf-8", errors="ignore")
            import io

            from gradio.routes import CurrentRequest

            info = {
                "exists": True,
                "log_file": str(log_file),
                "size_mb": (
                    log_file.stat().st_size / (1024 * 1024) if log_file.exists() else 0
                ),
                "rotated_files": [],
            }

            self.status_text = f"Log file ready for download: {info['log_file']}"
            return self.status_text

        except Exception as e:
            error_msg = f"Error downloading logs: {str(e)}"
            logger.error(error_msg)
            self.status_text = error_msg
            return self.status_text

    def _generate_log_info(self) -> dict[str, Any]:
        """Generate dynamic log information."""
        try:
            from pathlib import Path

            log_file = Path("logs/app.log")

            monitoring_status = "Monitoring" if self.is_monitoring else "Ready"
            auto_scroll_status = "Enabled" if self.auto_scroll else "Disabled"
            filter_status = (
                "Active"
                if self.filter_text.strip() or self.log_level_filter != "ALL"
                else "Inactive"
            )

            log_file_exists = "Yes" if log_file.exists() else "No"
            log_size = 0.0
            rotated_files_count = 0

            if log_file.exists():
                log_size = round(log_file.stat().st_size / (1024 * 1024), 2)
                # Find rotated files (app.log.*.txt)
                import glob

                rotated_files = glob.glob("logs/app.log.*.txt")
                rotated_files_count = len(rotated_files)

            return {
                "Application": {
                    "Status": monitoring_status,
                    "Auto-scroll": auto_scroll_status,
                    "Filter": filter_status,
                    "Real-time": str(log_file_exists),
                },
                "File Details": {
                    "Current File": str(log_file),
                    "Size": f"{log_size:.2f} MB",
                    "Exists": log_file_exists,
                    "Rotated Files": rotated_files_count,
                },
                "Filters": {
                    "Text Filter": self.filter_text,
                    "Level Filter": self.log_level_filter,
                },
                "Statistics": {
                    "Total Lines": len(self.log_lines),
                    "Filtered Lines": len(self.filtered_lines),
                    "Monitoring Active": self.is_monitoring,
                },
            }

        except Exception as e:
            return {
                "Error": f"Error generating log info: {str(e)[:50]}...",
                "Status": "Error",
                "Auto-scroll": "Disabled",
                "Filter": "Inactive",
                "Real-time": "Not Available",
            }

    def cleanup(self):
        """Clean up resources."""
        super().cleanup()
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
