"""
Logs Viewer Component

Migrates the NiceGUI Logs page to Gradio with real-time monitoring,
filtering, and async operations for log management.
"""

import gradio as gr
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
import threading
from datetime import datetime

from .base_component import AsyncComponent
from src.models.logging_service import logging_service, get_logger

logger = get_logger(__name__)


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
        self.log_lines: List[str] = []
        self.filtered_lines: List[str] = []
        
        # UI state
        self.status_text = "Ready"
    
    def create_tab(self):
        """Create the logs viewer tab."""
        with gr.Column(elem_classes="logs-container"):
            gr.Markdown("### Application Logs")
            
            # Filter controls
            with gr.Row():
                self.filter_input = gr.Textbox(
                    label="Filter logs",
                    placeholder="Enter text to filter logs...",
                    elem_classes="filter-input"
                )
                self.level_filter = gr.Dropdown(
                    choices=["ALL", "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                    value="ALL",
                    label="Log Level",
                    elem_classes="level-filter"
                )
                self.auto_scroll_checkbox = gr.Checkbox(
                    label="Auto-scroll",
                    value=True,
                    elem_classes="auto-scroll-checkbox"
                )
            
            # Controls
            with gr.Row():
                self.start_monitor_btn = gr.Button(
                    "Start Monitoring",
                    variant="primary",
                    elem_classes="start-monitor-btn"
                )
                self.stop_monitor_btn = gr.Button(
                    "Stop Monitoring",
                    elem_classes="stop-monitor-btn"
                )
                self.refresh_btn = gr.Button(
                    "Refresh",
                    elem_classes="refresh-btn"
                )
                self.clear_btn = gr.Button(
                    "Clear Logs",
                    variant="stop",
                    elem_classes="clear-btn"
                )
                self.download_btn = gr.Button(
                    "Download",
                    elem_classes="download-btn"
                )
            
            # Log display area
            self.logs_display = gr.Textbox(
                label="Application Logs",
                lines=20,
                interactive=False,
                elem_classes="logs-textbox"
            )
            
            # Status and information
            with gr.Row():
                self.status_label = gr.Textbox(
                    label="Status",
                    value="Ready",
                    interactive=False,
                    elem_classes="status-label"
                )
                self.line_count_label = gr.Textbox(
                    label="Line Count",
                    value="0 lines",
                    interactive=False,
                    elem_classes="line-count-label"
                )
            
            # Log information display
            self.log_info_display = gr.JSON(
                value={},
                label="Log Information",
                elem_classes="log-info-json"
            )
            
            # Event handlers
            self._setup_event_handlers()
            
            # Load initial logs
            # Note: Async initialization is handled separately in Gradio
    
    def _setup_event_handlers(self):
        """Set up event handlers for the logs viewer interface."""
        
        # Filter changes
        self.filter_input.change(
            fn=self._on_filter_change,
            inputs=[self.filter_input, self.level_filter],
            outputs=[self.logs_display, self.line_count_label, self.status_label],
            queue=True
        )
        
        self.level_filter.change(
            fn=self._on_level_filter_change,
            inputs=[self.filter_input, self.level_filter],
            outputs=[self.logs_display, self.line_count_label, self.status_label],
            queue=True
        )
        
        # Auto-scroll toggle
        self.auto_scroll_checkbox.change(
            fn=self._on_auto_scroll_change,
            inputs=[self.auto_scroll_checkbox],
            outputs=[self.status_label],
            queue=True
        )
        
        # Control buttons
        self.start_monitor_btn.click(
            fn=self._start_monitoring,
            inputs=[],
            outputs=[self.start_monitor_btn, self.stop_monitor_btn, self.status_label, self.log_info_display],
            queue=True
        )
        
        self.stop_monitor_btn.click(
            fn=self._stop_monitoring,
            inputs=[],
            outputs=[self.start_monitor_btn, self.stop_monitor_btn, self.status_label, self.log_info_display],
            queue=True
        )
        
        self.refresh_btn.click(
            fn=self._refresh_logs,
            inputs=[self.filter_input, self.level_filter],
            outputs=[self.logs_display, self.line_count_label, self.status_label, self.log_info_display],
            queue=True
        )
        
        self.clear_btn.click(
            fn=self._clear_logs,
            inputs=[],
            outputs=[self.logs_display, self.line_count_label, self.status_label],
            queue=True
        )
        
        self.download_btn.click(
            fn=self._download_logs,
            inputs=[],
            outputs=[self.status_label],
            queue=True
        )
    
    async def _load_initial_logs(self):
        """Load initial log entries."""
        try:
            self.log_lines = await self._get_recent_logs_async(200)
            self._apply_filters()
            self._update_log_display()
            self.status_text = "Loaded initial logs"
            
            return self.logs_display.value, self.line_count_label.value, self.status_text, self._generate_log_info()
            
        except Exception as e:
            error_msg = f"Error loading initial logs: {str(e)}"
            logger.error(error_msg)
            self.status_text = error_msg
            return "", "0 lines", self.status_text, {}
    
    async def _get_recent_logs_async(self, limit: int = 200) -> List[str]:
        """Get recent log entries asynchronously."""
        try:
            logs = await self.run_in_executor(logging_service.get_recent_logs, limit)
            return logs
        except Exception as e:
            logger.error(f"Error getting recent logs: {e}")
            return []
    
    async def _on_filter_change(self, filter_text: str, level_filter: str) -> tuple:
        """Handle filter text change."""
        self.filter_text = filter_text or ""
        self.log_level_filter = level_filter
        self._apply_filters()
        self._update_log_display()
        return self.logs_display.value, self.line_count_label.value, self.status_text
    
    async def _on_level_filter_change(self, filter_text: str, level_filter: str) -> tuple:
        """Handle log level filter change."""
        self.filter_text = filter_text or ""
        self.log_level_filter = level_filter
        self._apply_filters()
        self._update_log_display()
        return self.logs_display.value, self.line_count_label.value, self.status_text
    
    async def _on_auto_scroll_change(self, auto_scroll: bool) -> str:
        """Handle auto-scroll toggle change."""
        self.auto_scroll = auto_scroll
        return f"Auto-scroll {'enabled' if auto_scroll else 'disabled'}"
    
    async def _start_monitoring(self) -> tuple:
        """Start real-time log monitoring."""
        if self.is_monitoring:
            return self.start_monitor_btn, self.stop_monitor_btn, "Monitoring already active", self._generate_log_info()
        
        self.is_monitoring = True
        self.status_text = "Monitoring logs in real-time..."
        
        # Start monitoring task
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
        
        self.monitoring_task = asyncio.create_task(self._monitor_logs())
        
        return self.start_monitor_btn, self.stop_monitor_btn, self.status_text, self._generate_log_info()
    
    async def _stop_monitoring(self) -> tuple:
        """Stop real-time log monitoring."""
        if not self.is_monitoring:
            return self.start_monitor_btn, self.stop_monitor_btn, "Monitoring not active", self._generate_log_info()
        
        self.is_monitoring = False
        self.status_text = "Monitoring stopped"
        
        # Stop monitoring task
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
        
        # Update log information display
        log_info = self._generate_log_info()
        
        return self.start_monitor_btn, self.stop_monitor_btn, self.status_text, log_info
    
    async def _monitor_logs(self):
        """Background task for real-time log monitoring."""
        try:
            while self.is_monitoring:
                # Get new log lines
                new_lines = await self._get_recent_logs_async(50)
                
                if new_lines and len(new_lines) > len(self.log_lines):
                    # Add new lines
                    new_log_lines = new_lines[len(self.log_lines):]
                    self.log_lines.extend(new_log_lines)
                    
                    # Apply filters and update display
                    self._apply_filters()
                    self._update_log_display()
                
                # Wait before next check
                await asyncio.sleep(1)
                
        except asyncio.CancelledError:
            logger.info("Log monitoring task cancelled")
        except Exception as e:
            logger.error(f"Error in log monitoring: {e}")
            self.status_text = f"Error in monitoring: {str(e)}"
    
    def _apply_filters(self):
        """Apply current filters to log lines."""
        filtered = self.log_lines.copy()
        
        # Apply text filter
        if self.filter_text.strip():
            filter_lower = self.filter_text.lower()
            filtered = [line for line in filtered if filter_lower in line.lower()]
        
        # Apply log level filter
        if self.log_level_filter != "ALL":
            level_indicator = f"- {self.log_level_filter} -"
            filtered = [line for line in filtered if level_indicator in line]
        
        self.filtered_lines = filtered
    
    def _update_log_display(self):
        """Update the log display with filtered content."""
        if not self.filtered_lines:
            self.logs_display.value = "No logs found. Start monitoring to see real-time logs."
        else:
            # Show last 500 lines to prevent UI freezing
            display_lines = self.filtered_lines[-500:]
            # Join lines without extra spacing to avoid "useless lines"
            self.logs_display.value = "\n".join(display_lines)
        
        self.line_count_label.value = f"{len(self.filtered_lines)} lines"
        
        # Auto-scroll to bottom if enabled
        if self.auto_scroll:
            # Note: Gradio Textbox doesn't have built-in scroll control
            # This would need JavaScript injection or a custom component
            pass
    
    async def _refresh_logs(self, filter_text: str, level_filter: str) -> tuple:
        """Refresh the log display."""
        try:
            # Update filters
            self.filter_text = filter_text or ""
            self.log_level_filter = level_filter
            
            # Load fresh logs
            self.log_lines = await self._get_recent_logs_async(200)
            self._apply_filters()
            self._update_log_display()
            
            self.status_text = "Logs refreshed"
            
            return self.logs_display.value, self.line_count_label.value, self.status_text, self._generate_log_info()
            
        except Exception as e:
            error_msg = f"Error refreshing logs: {str(e)}"
            logger.error(error_msg)
            self.status_text = error_msg
            return self.logs_display.value, self.line_count_label.value, self.status_text, self._generate_log_info()
    
    async def _clear_logs(self) -> tuple:
        """Clear all logs."""
        try:
            if await self.run_in_executor(logging_service.clear_logs):
                self.log_lines = []
                self.filtered_lines = []
                self._update_log_display()
                self.status_text = "Logs cleared successfully"
            else:
                self.status_text = "Failed to clear logs"
            
            return self.logs_display.value, self.line_count_label.value, self.status_text
            
        except Exception as e:
            error_msg = f"Error clearing logs: {str(e)}"
            logger.error(error_msg)
            self.status_text = error_msg
            return self.logs_display.value, self.line_count_label.value, self.status_text
    
    async def _download_logs(self) -> str:
        """Download the current log file."""
        try:
            info = await self.run_in_executor(logging_service.get_log_file_info)
            if info["exists"]:
                self.status_text = f"Log file ready for download: {info['log_file']}"
                return self.status_text
            else:
                self.status_text = "No log file to download"
                return self.status_text
                
        except Exception as e:
            error_msg = f"Error downloading logs: {str(e)}"
            logger.error(error_msg)
            self.status_text = error_msg
            return self.status_text
    
    def _generate_log_info(self) -> Dict[str, Any]:
        """Generate dynamic log information."""
        try:
            info = logging_service.get_log_file_info()
            
            # Get current monitoring status
            monitoring_status = "Monitoring" if self.is_monitoring else "Ready"
            auto_scroll_status = "Enabled" if self.auto_scroll else "Disabled"
            filter_status = (
                "Active" 
                if self.filter_text.strip() or self.log_level_filter != "ALL" 
                else "Inactive"
            )
            real_time_status = "Available" if info.get("exists", False) else "Not Available"
            
            # Get log file details
            log_file = info.get("log_file", "Unknown")
            log_size = info.get("size_mb", 0)
            log_exists = "Yes" if info.get("exists", False) else "No"
            rotated_files = len(info.get("rotated_files", []))
            
            return {
                "Application": {
                    "Status": monitoring_status,
                    "Auto-scroll": auto_scroll_status,
                    "Filter": filter_status,
                    "Real-time": real_time_status
                },
                "File Details": {
                    "Current File": log_file,
                    "Size": f"{log_size:.2f} MB",
                    "Exists": log_exists,
                    "Rotated Files": rotated_files
                },
                "Filters": {
                    "Text Filter": self.filter_text,
                    "Level Filter": self.log_level_filter
                },
                "Statistics": {
                    "Total Lines": len(self.log_lines),
                    "Filtered Lines": len(self.filtered_lines),
                    "Monitoring Active": self.is_monitoring
                }
            }
            
        except Exception as e:
            return {
                "Error": f"Error generating log info: {str(e)[:50]}...",
                "Status": "Error",
                "Auto-scroll": "Disabled",
                "Filter": "Inactive",
                "Real-time": "Not Available"
            }
    
    def cleanup(self):
        """Clean up resources."""
        super().cleanup()
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()