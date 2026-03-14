"""
Logs Viewer Component - Native Gradio Features

Uses Gradio's native features:
- gr.Textbox for log display (Markdown supported)
- Simple click handlers with queue=True
"""

from datetime import datetime
from pathlib import Path

import gradio as gr


class LogsViewer:
    """
    Logs viewer component using Gradio's native features.

    Features:
    - Textbox component for log formatting (supports Markdown)
    - Simple click handlers with queue=True
    """

    def __init__(self):
        # Use state for log display
        self.log_display_value = "No logs available. Click 'Refresh Logs' to update."

    def create_tab(self) -> None:
        """Create the logs viewer tab with native Gradio components."""
        with gr.Column(elem_classes="logs-container"):
            gr.Markdown("### Logs Viewer 📋")

            # Log display - use Textbox component (supports Markdown)
            self.log_display = gr.Textbox(
                value=self.log_display_value,
                label="Logs",
                interactive=False,
                lines=20,
                max_lines=30,
            )

            # Status indicator
            self.status_text = gr.Textbox(
                label="Status", interactive=False, value="Ready"
            )

            # Action buttons
            with gr.Row():
                self.refresh_btn = gr.Button("🔄 Refresh Logs")
                self.clear_btn = gr.Button("🗑️ Clear History")

            # Setup event handlers
            self._setup_event_handlers()

    def _setup_event_handlers(self):
        """Set up event handlers using Gradio's native pattern."""

        self.refresh_btn.click(
            fn=self._refresh_logs,
            inputs=[],
            outputs=[self.log_display, self.status_text],
            queue=True,
        )

        self.clear_btn.click(
            fn=self._clear_logs,
            inputs=[],
            outputs=[self.log_display, self.status_text],
            queue=True,
        )

    def _refresh_logs(self) -> tuple[str, str]:
        """Refresh log display."""
        try:
            logs = []

            # Get recent logs from file system
            logs_dir = Path("logs")
            if logs_dir.exists():
                logfile_names = sorted(
                    [f.name for f in logs_dir.glob("*.*")], reverse=True
                )

                for filename in logfile_names[:3]:  # Limit to last 3 log files
                    filepath = logs_dir / filename
                    logs.append(f"\n**{filename}**\n```")
                    with open(filepath, encoding="utf-8", errors="ignore") as f:
                        count = 0
                        for line in reversed(f):
                            if count < 50:
                                logs.append(line.rstrip())
                            count += 1
                    logs.append("```\n")

            if logs:
                log_text = "\n".join(logs)
                return f"📄 Loaded {len(logfile_names)} log file(s)", log_text
            else:
                return "No logs found", "Logs directory is empty"

        except Exception as e:
            return f"❌ Error loading logs: {str(e)}", str(e)

    def _clear_logs(self) -> tuple[str, str]:
        """Clear log history."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Move logs to backup if they exist
            logs_dir = Path("logs")
            if logs_dir.exists():
                for logfile in list(logs_dir.glob("*.*")):
                    backup_path = Path(f"logs_backup/{timestamp}/{logfile.name}")
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    logfile.rename(backup_path)

            return (
                "✅ Logs cleared",
                "**Logs cleared**\n\nRecent logs have been backed up.",
            )
        except Exception as e:
            return f"❌ Error clearing logs: {str(e)}", str(e)

    def cleanup(self):
        """Clean up resources."""
        pass
