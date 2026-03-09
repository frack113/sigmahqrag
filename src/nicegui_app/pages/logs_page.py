"""
Logs Page for SigmaHQ RAG Application

This page displays application logs with real-time updates, filtering, and management controls.
"""

from nicegui import ui, app
from typing import List, Optional
import asyncio
import threading
from datetime import datetime

from ..models.logging_service import logging_service, get_logger

logger = get_logger(__name__)

# Global state
log_lines: List[str] = []
filtered_lines: List[str] = []
is_monitoring = False
filter_text = ""
log_level_filter = "ALL"
auto_scroll = True
status_label = None
monitor_button = None
log_content = None
line_count_label = None
log_container = None
log_info_display = None


def load_initial_logs():
    """Load initial log entries."""
    global log_lines, filtered_lines
    try:
        log_lines = logging_service.get_recent_logs(200)
        apply_filters()
        update_log_display()
        status_label.set_text("Loaded initial logs")
    except Exception as e:
        logger.error(f"Error loading initial logs: {e}")
        status_label.set_text(f"Error loading logs: {e}")


def on_filter_change(event):
    """Handle filter text change."""
    global filter_text
    filter_text = event.value or ""
    apply_filters()
    update_log_display()


def on_level_filter_change(event):
    """Handle log level filter change."""
    global log_level_filter
    log_level_filter = event.value
    apply_filters()
    update_log_display()


def apply_filters():
    """Apply current filters to log lines."""
    global log_lines, filtered_lines
    filtered = log_lines.copy()

    # Apply text filter
    if filter_text.strip():
        filter_lower = filter_text.lower()
        filtered = [line for line in filtered if filter_lower in line.lower()]

    # Apply log level filter
    if log_level_filter != "ALL":
        level_indicator = f"- {log_level_filter} -"
        filtered = [line for line in filtered if level_indicator in line]

    filtered_lines = filtered


def update_log_display():
    """Update the log display with filtered content."""
    global filtered_lines
    if not filtered_lines:
        log_content.set_text("No logs found. Start monitoring to see real-time logs.")
    else:
        # Show last 500 lines to prevent UI freezing
        display_lines = filtered_lines[-500:]
        # Join lines without extra spacing to avoid "useless lines"
        log_content.set_text("\n".join(display_lines))

    line_count_label.set_text(f"{len(filtered_lines)} lines")

    # Auto-scroll to bottom if enabled
    if auto_scroll:
        scroll_to_bottom()


def scroll_to_bottom():
    """Scroll the log container to the bottom."""
    # Use JavaScript to scroll to bottom
    log_container.run_method("scrollTo", {"top": 999999, "behavior": "smooth"})


def refresh_logs():
    """Refresh the log display."""
    load_initial_logs()
    status_label.set_text("Logs refreshed")


def clear_logs():
    """Clear all logs."""

    def confirm_clear():
        if logging_service.clear_logs():
            load_initial_logs()
            status_label.set_text("Logs cleared successfully")
        else:
            status_label.set_text("Failed to clear logs")
        app.native.main_window.evaluate_js(
            'window.dispatchEvent(new CustomEvent("close-confirm-dialog"))'
        )

    # Show confirmation dialog
    app.native.main_window.evaluate_js(f"""
        window.dispatchEvent(new CustomEvent("show-confirm-dialog", {{
            detail: {{
                title: "Clear Logs",
                message: "Are you sure you want to clear all logs? This action cannot be undone.",
                onConfirm: {confirm_clear}
            }}
        }}))
    """)


def download_logs():
    """Download the current log file."""
    try:
        info = logging_service.get_log_file_info()
        if info["exists"]:
            # Create a download link
            status_label.set_text(f"Log file ready for download: {info['log_file']}")
            # In a real implementation, you might want to create a temporary download link
            # or use NiceGUI's file download functionality
        else:
            status_label.set_text("No log file to download")
    except Exception as e:
        status_label.set_text(f"Error downloading logs: {e}")


def toggle_monitoring():
    """Start or stop log monitoring."""
    global is_monitoring
    if is_monitoring:
        stop_monitoring()
    else:
        start_monitoring()


def start_monitoring():
    """Start real-time log monitoring."""
    global is_monitoring
    if is_monitoring:
        return

    is_monitoring = True
    monitor_button.set_text("Stop Monitoring").props("color=red")
    monitor_button.props("icon=stop")
    status_label.set_text("Monitoring logs in real-time...")

    # Start monitoring with callback
    logging_service.start_monitoring(on_new_log_line, interval=0.5)


def update_log_info_display():
    """Update the log information display with current data."""
    global log_info_display
    if log_info_display:
        log_info_table = generate_log_info_table()
        log_info_display.set_content(log_info_table)


def stop_monitoring():
    """Stop real-time log monitoring."""
    global is_monitoring
    if not is_monitoring:
        return

    is_monitoring = False
    monitor_button.set_text("Start Monitoring").props("color=default")
    monitor_button.props("icon=play_arrow")
    status_label.set_text("Monitoring stopped")

    # Update log information display
    update_log_info_display()

    # Stop monitoring
    logging_service.stop_monitoring()


def on_new_log_line(line: str):
    """Handle new log line from monitoring."""
    global log_lines, filtered_lines
    # Add to log lines
    log_lines.append(line)

    # Apply filters and update display
    apply_filters()

    # Update display (only if we have new filtered lines)
    if len(filtered_lines) > 0:
        # Show last 500 lines
        display_lines = filtered_lines[-500:]
        # Join lines without extra spacing to avoid "useless lines"
        log_content.set_text("\n".join(display_lines))

        # Update line count
        line_count_label.set_text(f"{len(filtered_lines)} lines")

        # Auto-scroll if enabled
        if auto_scroll:
            scroll_to_bottom()


def generate_log_info_table():
    """Generate dynamic markdown table with current log information."""
    try:
        info = logging_service.get_log_file_info()

        # Get current monitoring status
        monitoring_status = "Monitoring" if is_monitoring else "Ready"
        auto_scroll_status = "Enabled" if auto_scroll else "Disabled"
        filter_status = (
            "Active" if filter_text.strip() or log_level_filter != "ALL" else "Inactive"
        )
        real_time_status = "Available" if info.get("exists", False) else "Not Available"

        # Get log file details
        log_file = info.get("log_file", "Unknown")
        log_size = info.get("size_mb", 0)
        log_exists = "Yes" if info.get("exists", False) else "No"
        rotated_files = len(info.get("rotated_files", []))

        return f"""
            📊 Log Information
            
            **🛠️ Application:**
             **Status:** {monitoring_status}
             **Auto-scroll:** {auto_scroll_status}
             **Filter:** {filter_status}
             **Real-time:** {real_time_status}
            
            **📁 File Details:**
             **Current File:** `{log_file}`
             **Size:** {log_size:.2f} MB
             **Exists:** {log_exists}
             **Rotated Files:** {rotated_files}
        """
    except Exception as e:
        return f"""
            ### 📊 Log Information
            | **Status** | **Auto-scroll** | **Filter** | **Real-time** |
            |------------|----------------|------------|---------------|
            | Error: {str(e)[:50]}... | Disabled | Inactive | Not Available |
            
            **📁 File Details:**
            - **Current File:** Unknown
            - **Size:** 0.00 MB
            - **Exists:** No
            - **Rotated Files:** 0
        """


def initialize_page():
    """Initialize the logs page."""
    global status_label, monitor_button, log_content, line_count_label, log_container

    # Main container with consistent layout
    main_container = ui.column().classes("w-full h-[90vh] bg-gray-100")

    with main_container:
        # Status bar
        with ui.row().classes("gap-3 flex-wrap"):
            status_label = ui.label("Ready")
            ui.label(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            ui.button("Refresh", icon="refresh", on_click=refresh_logs).props("outline")
            ui.button("Clear", icon="delete", on_click=clear_logs).props(
                "outline color=red"
            )
            ui.button("Download", icon="download", on_click=download_logs).props(
                "outline"
            )

        # Log information
        with ui.card().classes("w-full p-4 mb-4 bg-blue-50"):
            # Initialize log info table with default values
            log_info_table = generate_log_info_table()
            log_info_display = ui.markdown(log_info_table)

        # Filters and controls
        with ui.card().classes("w-full p-4 mb-4"):
            with ui.row().classes("w-full gap-4 items-end"):
                # Filter input
                filter_input = (
                    ui.input(
                        label="Filter logs", placeholder="Enter text to filter logs..."
                    )
                    .classes("flex-1")
                    .on("input", on_filter_change)
                )

                # Log level filter
                level_filter = (
                    ui.select(
                        options=[
                            "ALL",
                            "DEBUG",
                            "INFO",
                            "WARNING",
                            "ERROR",
                            "CRITICAL",
                        ],
                        value="ALL",
                        label="Log Level",
                    )
                    .classes("w-32")
                    .on("update:model-value", on_level_filter_change)
                )

                # Auto-scroll toggle
                ui.checkbox("Auto-scroll", value=True).classes("ml-2").bind_value(
                    globals(), "auto_scroll"
                )

                # Start/Stop monitoring
                monitor_button = ui.button(
                    "Start Monitoring",
                    icon="play_arrow",
                    on_click=toggle_monitoring,
                ).props("outline")

        # Log display area - use remaining space
        with ui.card().classes("w-full flex-1 p-0"):
            # Log header
            with ui.row().classes("w-full bg-gray-100 p-2 border-b"):
                ui.label("Log Entries").classes("font-semibold text-gray-700")
                line_count_label = ui.label("0 lines").classes(
                    "ml-auto text-sm text-gray-600"
                )

            # Log content area - use remaining space in card
            with ui.column().classes(
                "w-full flex-1 overflow-auto p-2 bg-black text-green-400 font-mono text-sm"
            ) as log_container:
                log_content = ui.label("").classes("whitespace-pre-wrap")
                load_initial_logs()
